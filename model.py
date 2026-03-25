from __future__ import annotations

import argparse
import re
import io
import itertools
import json
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
from xml.etree import ElementTree as ET

import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

LFS_ZIP = DATA_DIR / "LFS 2024" / "Egypt 2024-LFS STATA-V1.zip"
LFS_MEMBER = "Egypt 2024-LFS IND-V1.dta"
FINDEX_CSV = DATA_DIR / "FINDEX 2024" / "Findex_Microdata_2025_Egypt, Arab Rep..csv"
FINDEX_GROUPED_DOCX = DATA_DIR / "FINDEX 2024" / "findex_variables_grouped.docx"
ELMPS_PT1_RAR = DATA_DIR / "ELMPS 2023" / "elmps 2023 xs v2.1 pt 1.rar"
ELMPS_PT1_MEMBER = "elmps 2023 xs v2.1 pt 1.dta"
ELMPS_PT3_RAR = DATA_DIR / "ELMPS 2023" / "elmps 2023 xs v2.1 pt 3.rar"
ELMPS_PT3_MEMBER = "elmps 2023 xs v2.1 pt 3.dta"
SCHEMA_DOC_PATH = ROOT / "docs" / "egypt_synthetic_population_schema.md"

CORE_COLUMNS = ["sex", "age_band", "education_level", "urban_rural", "in_workforce"]
CORE_STATE_NAMES = {
    "sex": [0, 1],
    "age_band": [1, 2, 3, 4, 5, 6],
    "education_level": [1, 2, 3, 4],
    "urban_rural": [0, 1],
    "in_workforce": [0, 1],
}

LFS_EXTRA_RAW = [
    "reg",
    "mart",
    "emps",
    "occ_08",
    "ind",
    "sector",
    "wrkplc",
    "empstab",
    "empcont",
    "hlthins",
    "socsec",
    "estab",
    "numwrk",
    "hrswk",
    "totwag",
    "empinc",
    "sempinc",
    "secjob",
]

ELMPS_EXTRA_RAW = [
    "usempstp",
    "usformal",
    "usfirm_size",
    "ussocinsp",
    "uscontrp",
    "usmedins",
    "uspdleave",
    "uspdsick",
    "scjob",
    "q12102",
    "q12104",
    "q12201",
    "q12202",
    "q12203",
    "q12204",
    "q12205",
    "q12207",
    "q12208",
    "q12210",
    "q12213",
    "q12216",
    "q12217",
    "q12229",
    "q12230",
]

FINDEX_IDENTIFIER_COLUMNS = {
    "year",
    "economy",
    "economycode",
    "regionwb",
    "pop_adult",
    "wpid_random",
    "wgt",
}
FINDEX_CORE_RAW = {"female", "age", "educ", "emp_in", "urbanicity"}
MISSING_CODE = -1
SURVEY_MISSING_VALUES = {
    97,
    98,
    99,
    997,
    998,
    999,
    9997,
    9998,
    9999,
    99997,
    99998,
    99999,
    999997,
    999998,
    999999,
    9999997,
    9999998,
    9999999,
    999999996,
    999999997,
    999999998,
    999999999,
    9999999996,
    9999999997,
    9999999998,
    9999999999,
}
ELMPS_SME_SLOT_RANGE = range(1, 6)
ELMPS_SME_BASE_COLUMNS = [
    "q15104_1",
    "q15106",
    "q15107",
    "q15108",
    "q15109",
    "q15110",
    "q15111",
    "q15112",
    "q15113",
    "q15114",
    "q15115",
    "q15116",
    "q15117",
    "q15118",
    "q15120",
    "q15201",
    "q15202",
    "q15202_1",
    "q15203",
    "q15204",
    "q15205",
    "q15207",
    "q15304_1",
    "q15304_13",
    "q15401",
    "q15405",
]


def patch_statsmodels_for_pgmpy() -> None:
    """
    pgmpy 0.1.24 imports statsmodels through an API path that is incompatible
    with the statsmodels build installed in this environment. This patch keeps
    pgmpy usable without changing site-packages.
    """
    import statsmodels.compat.pandas as sm_pandas

    current = sm_pandas.deprecate_kwarg
    if getattr(current, "_escwa_patch_applied", False):
        return

    original = current

    def patched_deprecate_kwarg(*args, **kwargs):
        # First try the environment-native signature.
        try:
            return original(*args, **kwargs)
        except TypeError as exc:
            # pgmpy 0.1.24 can call this through a legacy signature path.
            # If that path fails due to signature mismatch, retry with an
            # explicit warning class prepended.
            if args and isinstance(args[0], str):
                try:
                    return original(FutureWarning, *args, **kwargs)
                except TypeError:
                    pass
            raise exc

    patched_deprecate_kwarg._escwa_patch_applied = True  # type: ignore[attr-defined]
    sm_pandas.deprecate_kwarg = patched_deprecate_kwarg


patch_statsmodels_for_pgmpy()

from pgmpy.estimators import BicScore, HillClimbSearch  # noqa: E402
from pgmpy.models import BayesianNetwork  # noqa: E402
from pgmpy.readwrite import BIFWriter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Learn and sample an Egypt synthetic population with persons and SMEs."
    )
    parser.add_argument(
        "--sample-sizes",
        type=int,
        nargs="+",
        default=[1000, 10000],
        help="Synthetic person population sizes to draw.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--max-core-indegree",
        type=int,
        default=2,
        help="Maximum indegree when learning the LFS core DAG.",
    )
    parser.add_argument(
        "--max-extra-parents",
        type=int,
        default=3,
        help="Maximum number of core parents allowed for any extra variable.",
    )
    parser.add_argument(
        "--skip-sample",
        action="store_true",
        help="Only fit and save the model; do not draw a synthetic sample.",
    )
    return parser.parse_args()


def age_to_band(series: pd.Series) -> pd.Series:
    bins = [15, 25, 35, 45, 55, 65, np.inf]
    labels = [1, 2, 3, 4, 5, 6]
    return pd.cut(series, bins=bins, right=False, labels=labels)


def sanitize_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.mask(values.isin(SURVEY_MISSING_VALUES))


def map_yes_no_binary(series: pd.Series, yes: int = 1, no: int = 2) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").map({yes: 1, no: 0})


def discretize_positive_quantiles(series: pd.Series, bins: int = 5) -> pd.Series:
    values = sanitize_numeric(series)
    out = pd.Series(MISSING_CODE, index=series.index, dtype="int64")
    valid = values.notna() & (values > 0)
    if valid.sum() == 0:
        return out

    unique_count = int(values[valid].nunique())
    q = max(1, min(bins, unique_count))
    if q == 1:
        out.loc[valid] = 1
        return out

    discretized = pd.qcut(values[valid], q=q, labels=False, duplicates="drop")
    out.loc[valid] = discretized.astype(int) + 1
    return out


def discretize_nonnegative_quantiles(series: pd.Series, bins: int = 5) -> pd.Series:
    values = sanitize_numeric(series)
    out = pd.Series(MISSING_CODE, index=series.index, dtype="int64")
    zero_mask = values.notna() & (values == 0)
    out.loc[zero_mask] = 0

    positive = values.notna() & (values > 0)
    if positive.sum() == 0:
        return out

    unique_count = int(values[positive].nunique())
    q = max(1, min(bins, unique_count))
    if q == 1:
        out.loc[positive] = 1
        return out

    discretized = pd.qcut(values[positive], q=q, labels=False, duplicates="drop")
    out.loc[positive] = discretized.astype(int) + 1
    return out


def enterprise_start_year_to_band(series: pd.Series, reference_year: int = 2023) -> pd.Series:
    years = sanitize_numeric(series)
    valid = years.notna() & years.between(1900, reference_year)
    ages = pd.Series(np.nan, index=series.index, dtype="float64")
    ages.loc[valid] = reference_year - years.loc[valid]
    bins = [-0.1, 2, 5, 10, 20, 40, np.inf]
    labels = [1, 2, 3, 4, 5, 6]
    return pd.cut(ages, bins=bins, labels=labels, right=False)


def finalize_discrete_frame(df: pd.DataFrame, core_columns: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")

    out = out.dropna(subset=list(core_columns)).copy()

    for column in out.columns:
        out[column] = out[column].fillna(MISSING_CODE).round().astype(int)

    return out.reset_index(drop=True)


def build_state_names(
    df: pd.DataFrame,
    fixed_state_names: Dict[str, Sequence[int]] | None = None,
) -> Dict[str, List[int]]:
    state_names: Dict[str, List[int]] = {}

    if fixed_state_names:
        for column, states in fixed_state_names.items():
            if column in df.columns:
                state_names[column] = [int(state) for state in states]

    for column in df.columns:
        if column in state_names:
            continue
        observed = pd.to_numeric(df[column], errors="coerce").dropna().astype(int).unique().tolist()
        state_names[column] = sorted(int(state) for state in observed)

    return state_names


def read_stata_from_zip(zip_path: Path, member: str, columns: Sequence[str]) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as archive:
        data = archive.read(member)
    return pd.read_stata(io.BytesIO(data), columns=list(columns), convert_categoricals=False)


def read_stata_from_rar(rar_path: Path, member: str, columns: Sequence[str]) -> pd.DataFrame:
    proc = subprocess.run(
        ["tar", "-xOf", str(rar_path), member],
        check=True,
        capture_output=True,
    )
    return pd.read_stata(io.BytesIO(proc.stdout), columns=list(columns), convert_categoricals=False)


def read_docx_lines(path: Path) -> List[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")

    root = ET.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines: List[str] = []

    for para in root.findall(".//w:p", namespace):
        text = "".join(t.text for t in para.findall(".//w:t", namespace) if t.text).strip()
        if text:
            lines.append(text)

    return lines


def load_findex_grouped_variables() -> List[str]:
    lines = read_docx_lines(FINDEX_GROUPED_DOCX)
    vars_in_doc: List[str] = []
    seen = set()
    ignore = {"Global", "SURVEY", "Basic", "This", "QUESTIONS", "CATEGORIES", "SUMMARY"}

    for line in lines:
        token = line.split()[0]
        token = token.strip().rstrip(":")
        if token in ignore:
            continue
        if token and token[0].isalpha() and all(ch.isalnum() or ch == "_" for ch in token):
            if token not in seen:
                seen.add(token)
                vars_in_doc.append(token)

    return vars_in_doc


def preprocess_lfs() -> Tuple[pd.DataFrame, List[str]]:
    raw_columns = ["sex", "age", "educ", "rururb", "lfs", *LFS_EXTRA_RAW]
    raw = read_stata_from_zip(LFS_ZIP, LFS_MEMBER, raw_columns)
    raw = raw.loc[raw["age"] >= 15].copy()

    out = pd.DataFrame(index=raw.index)
    out["sex"] = raw["sex"].map({1: 0, 2: 1})
    out["age_band"] = age_to_band(raw["age"])
    out["education_level"] = raw["educ"].map({1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 4})
    out["urban_rural"] = raw["rururb"].map({1: 0, 0: 1})
    out["in_workforce"] = raw["lfs"].map({1: 1, 2: 0})

    out["lfs_region"] = raw["reg"]
    out["lfs_marital_status"] = raw["mart"]
    out["lfs_employment_status"] = raw["emps"]
    out["lfs_occupation_group"] = raw["occ_08"]
    out["lfs_industry_group"] = raw["ind"]
    out["lfs_sector"] = raw["sector"]
    out["lfs_workplace_type"] = raw["wrkplc"]
    out["lfs_job_stability"] = raw["empstab"]
    out["lfs_contract_type"] = raw["empcont"]
    out["lfs_health_insurance"] = raw["hlthins"]
    out["lfs_social_security"] = raw["socsec"]
    out["lfs_works_in_establishment"] = raw["estab"]
    out["lfs_establishment_size_band"] = raw["numwrk"]
    out["lfs_has_secondary_job"] = raw["secjob"]
    out["lfs_weekly_hours_band"] = discretize_positive_quantiles(raw["hrswk"])
    out["lfs_monthly_wage_band"] = discretize_positive_quantiles(raw["totwag"])
    out["lfs_employer_income_band"] = discretize_positive_quantiles(raw["empinc"])
    out["lfs_self_employed_income_band"] = discretize_positive_quantiles(raw["sempinc"])

    out = finalize_discrete_frame(out, CORE_COLUMNS)
    extra_columns = [col for col in out.columns if col not in CORE_COLUMNS]
    return out, extra_columns


def preprocess_findex() -> Tuple[pd.DataFrame, List[str], List[str], List[str]]:
    grouped_doc_vars = load_findex_grouped_variables()
    csv_columns = pd.read_csv(FINDEX_CSV, nrows=1).columns.tolist()
    present_doc_vars = [var for var in grouped_doc_vars if var in csv_columns]
    missing_doc_vars = [var for var in grouped_doc_vars if var not in csv_columns]

    raw = pd.read_csv(FINDEX_CSV, usecols=present_doc_vars)

    out = pd.DataFrame(index=raw.index)
    out["sex"] = raw["female"].map({2: 0, 1: 1})
    out["age_band"] = age_to_band(raw["age"])
    out["education_level"] = raw["educ"].map({1: 1, 2: 2, 3: 4})
    out["urban_rural"] = raw["urbanicity"].map({2: 0, 1: 1})
    out["in_workforce"] = raw["emp_in"].map({1: 1, 2: 0})

    for column in present_doc_vars:
        if column in FINDEX_IDENTIFIER_COLUMNS or column in FINDEX_CORE_RAW:
            continue
        out[f"findex_{column}"] = raw[column]

    out = finalize_discrete_frame(out, CORE_COLUMNS)
    extra_columns = [col for col in out.columns if col not in CORE_COLUMNS]
    return out, extra_columns, present_doc_vars, missing_doc_vars


def reshape_elmps_enterprises() -> pd.DataFrame:
    raw_columns = ["hhid", *[f"{base}_{slot}" for base in ELMPS_SME_BASE_COLUMNS for slot in ELMPS_SME_SLOT_RANGE]]
    raw = read_stata_from_rar(ELMPS_PT3_RAR, ELMPS_PT3_MEMBER, raw_columns)

    long_frames: List[pd.DataFrame] = []
    for slot in ELMPS_SME_SLOT_RANGE:
        keep_columns = ["hhid", *[f"{base}_{slot}" for base in ELMPS_SME_BASE_COLUMNS]]
        temp = raw[keep_columns].copy()
        temp.columns = ["hhid", *ELMPS_SME_BASE_COLUMNS]
        temp["enterprise_slot"] = slot
        temp = temp.loc[temp[ELMPS_SME_BASE_COLUMNS].notna().any(axis=1)].copy()
        long_frames.append(temp)

    long = pd.concat(long_frames, ignore_index=True)
    long = long.drop_duplicates(subset=["hhid", "enterprise_slot"]).reset_index(drop=True)
    return long


def load_elmps_person_frame() -> pd.DataFrame:
    raw_columns = [
        "hhid",
        "indid",
        "pn",
        "expan_hh",
        "sex",
        "age",
        "educ",
        "urban",
        "crwrkst1",
        *ELMPS_EXTRA_RAW,
    ]
    raw = read_stata_from_rar(ELMPS_PT1_RAR, ELMPS_PT1_MEMBER, raw_columns)
    return raw.loc[raw["age"] >= 15].copy()


def preprocess_elmps() -> Tuple[pd.DataFrame, List[str]]:
    raw = load_elmps_person_frame()
    enterprise_counts = (
        reshape_elmps_enterprises()
        .dropna(subset=["q15405"])
        .groupby(["hhid", "q15405"])
        .size()
        .rename("elmps_num_enterprises_managed")
        .reset_index()
        .rename(columns={"q15405": "pn"})
    )
    raw = raw.merge(enterprise_counts, on=["hhid", "pn"], how="left")
    raw["elmps_num_enterprises_managed"] = (
        raw["elmps_num_enterprises_managed"].fillna(0).astype(int)
    )

    out = pd.DataFrame(index=raw.index)
    out["sex"] = raw["sex"].map({1: 0, 2: 1})
    out["age_band"] = age_to_band(raw["age"])
    out["education_level"] = raw["educ"].map({1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 6: 4, 7: 4})
    out["urban_rural"] = raw["urban"].map({1: 0, 2: 1})
    out["in_workforce"] = raw["crwrkst1"].map({1: 1, 2: 1, 3: 0})

    out["elmps_employment_status"] = raw["usempstp"]
    out["elmps_job_formality"] = raw["usformal"]
    out["elmps_firm_size_band"] = raw["usfirm_size"]
    out["elmps_social_insurance_job"] = raw["ussocinsp"]
    out["elmps_has_job_contract"] = raw["uscontrp"]
    out["elmps_medical_insurance_job"] = raw["usmedins"]
    out["elmps_paid_leave_job"] = raw["uspdleave"]
    out["elmps_paid_sick_leave_job"] = raw["uspdsick"]
    out["elmps_has_secondary_job"] = raw["scjob"]
    out["elmps_owns_mobile_phone"] = raw["q12102"]
    out["elmps_has_mobile_wallet"] = raw["q12104"]
    out["elmps_has_any_savings"] = raw["q12201"]
    out["elmps_savings_method"] = raw["q12202"]
    out["elmps_savings_interest_bearing"] = raw["q12203"]
    out["elmps_applied_formal_loan_last12m"] = raw["q12204"]
    out["elmps_formal_loan_outcome"] = raw["q12205"]
    out["elmps_formal_lender_type"] = raw["q12207"]
    out["elmps_formal_loan_purpose"] = raw["q12208"]
    out["elmps_formal_loan_cost_type"] = raw["q12210"]
    out["elmps_borrowed_from_individuals_last12m"] = raw["q12213"]
    out["elmps_amount_borrowed_from_individuals_band"] = discretize_positive_quantiles(raw["q12216"])
    out["elmps_informal_loan_cost_type"] = raw["q12217"]
    out["elmps_has_bank_account"] = raw["q12229"]
    out["elmps_bank_savings_amount_band"] = discretize_positive_quantiles(raw["q12230"])
    out["elmps_num_enterprises_managed"] = raw["elmps_num_enterprises_managed"]
    out["elmps_manages_sme"] = (raw["elmps_num_enterprises_managed"] > 0).astype(int)

    out = finalize_discrete_frame(out, CORE_COLUMNS)
    extra_columns = [col for col in out.columns if col not in CORE_COLUMNS]
    return out, extra_columns


def preprocess_smes() -> Tuple[pd.DataFrame, List[str]]:
    persons = load_elmps_person_frame()[
        ["hhid", "pn", "sex", "age", "educ", "urban", "crwrkst1"]
    ].copy()
    enterprises = reshape_elmps_enterprises().dropna(subset=["q15405"]).copy()
    enterprises = enterprises.merge(
        persons,
        left_on=["hhid", "q15405"],
        right_on=["hhid", "pn"],
        how="left",
    )

    hires_external = map_yes_no_binary(enterprises["q15201"])
    social_insurance = map_yes_no_binary(enterprises["q15203"])
    new_workers = map_yes_no_binary(enterprises["q15205"])
    workers_left = map_yes_no_binary(enterprises["q15207"])

    out = pd.DataFrame(index=enterprises.index)
    out["sex"] = enterprises["sex"].map({1: 0, 2: 1})
    out["age_band"] = age_to_band(enterprises["age"])
    out["education_level"] = enterprises["educ"].map({1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 6: 4, 7: 4})
    out["urban_rural"] = enterprises["urban"].map({1: 0, 2: 1})
    out["in_workforce"] = enterprises["crwrkst1"].map({1: 1, 2: 1, 3: 0})

    out["sme_enterprise_activity_1digit"] = enterprises["q15104_1"]
    out["sme_enterprise_age_band"] = enterprise_start_year_to_band(enterprises["q15106"])
    out["sme_ownership_structure"] = enterprises["q15107"]
    out["sme_household_ownership_share_band"] = discretize_nonnegative_quantiles(enterprises["q15108"])
    out["sme_workplace_type"] = enterprises["q15109"]
    out["sme_current_capital_band"] = sanitize_numeric(enterprises["q15110"])
    out["sme_startup_capital_band"] = sanitize_numeric(enterprises["q15111"])
    out["sme_startup_capital_source"] = sanitize_numeric(enterprises["q15112"])
    out["sme_primary_buyer_type"] = sanitize_numeric(enterprises["q15113"])
    out["sme_has_business_license"] = map_yes_no_binary(enterprises["q15114"])
    out["sme_has_commercial_registration"] = map_yes_no_binary(enterprises["q15115"])
    out["sme_keeps_accounting_books"] = map_yes_no_binary(enterprises["q15116"])
    out["sme_has_online_page_or_storefront"] = map_yes_no_binary(enterprises["q15117"])
    out["sme_has_mobile_sales_app"] = map_yes_no_binary(enterprises["q15118"])
    out["sme_share_of_sales_online_band"] = discretize_nonnegative_quantiles(enterprises["q15120"])
    out["sme_hires_nonhousehold_workers"] = hires_external
    out["sme_num_nonhousehold_workers_band"] = discretize_nonnegative_quantiles(enterprises["q15202"])
    out["sme_num_related_external_workers_band"] = discretize_nonnegative_quantiles(enterprises["q15202_1"])
    out["sme_any_workers_with_social_insurance"] = social_insurance
    out["sme_num_workers_with_social_insurance_band"] = discretize_nonnegative_quantiles(
        enterprises["q15204"]
    )
    out["sme_new_workers_joined_last12m"] = new_workers
    out["sme_workers_left_last12m"] = workers_left
    out["sme_annual_wage_bill_band"] = discretize_nonnegative_quantiles(enterprises["q15304_1"])
    out["sme_annual_taxes_paid_band"] = discretize_nonnegative_quantiles(enterprises["q15304_13"])
    out["sme_average_monthly_net_earnings_band"] = discretize_nonnegative_quantiles(
        enterprises["q15401"]
    )

    no_external_workers = hires_external == 0
    for column in [
        "sme_num_nonhousehold_workers_band",
        "sme_num_related_external_workers_band",
        "sme_num_workers_with_social_insurance_band",
        "sme_annual_wage_bill_band",
    ]:
        out.loc[no_external_workers, column] = 0

    for column in [
        "sme_any_workers_with_social_insurance",
        "sme_new_workers_joined_last12m",
        "sme_workers_left_last12m",
    ]:
        out.loc[no_external_workers, column] = 0

    out = finalize_discrete_frame(out, CORE_COLUMNS)
    extra_columns = [column for column in out.columns if column not in CORE_COLUMNS]
    return out, extra_columns


def learn_core_model(core_data: pd.DataFrame, max_indegree: int) -> BayesianNetwork:
    state_names = build_state_names(core_data, CORE_STATE_NAMES)
    search = HillClimbSearch(core_data)
    dag = search.estimate(
        scoring_method=BicScore(core_data, state_names=state_names),
        max_indegree=max_indegree,
        show_progress=False,
    )

    model = BayesianNetwork(dag.edges())
    model.add_nodes_from(core_data.columns)
    model.fit(core_data, state_names=state_names, n_jobs=1)
    return model


def choose_best_core_parents(
    data: pd.DataFrame,
    child: str,
    candidate_parents: Sequence[str],
    max_parents: int,
) -> List[str]:
    if data[child].nunique(dropna=False) <= 1:
        return []

    score_data = data[[*candidate_parents, child]]
    score = BicScore(score_data, state_names=build_state_names(score_data, CORE_STATE_NAMES))
    best_score = score.local_score(child, [])
    best_parents: List[str] = []

    upper = min(max_parents, len(candidate_parents))
    for parent_count in range(1, upper + 1):
        for parents in itertools.combinations(candidate_parents, parent_count):
            local_score = score.local_score(child, list(parents))
            if local_score > best_score:
                best_score = local_score
                best_parents = list(parents)

    return best_parents


def learn_dataset_enrichment_model(
    data: pd.DataFrame,
    core_columns: Sequence[str],
    extra_columns: Sequence[str],
    core_edges: Iterable[Tuple[str, str]],
    max_extra_parents: int,
) -> Tuple[BayesianNetwork, Dict[str, List[str]]]:
    parent_map: Dict[str, List[str]] = {}
    extra_edges: List[Tuple[str, str]] = []

    for extra in extra_columns:
        parents = choose_best_core_parents(data, extra, core_columns, max_extra_parents)
        parent_map[extra] = parents
        extra_edges.extend((parent, extra) for parent in parents)

    fit_data = data[list(core_columns) + list(extra_columns)]
    model = BayesianNetwork(list(core_edges) + extra_edges)
    model.add_nodes_from(fit_data.columns)
    model.fit(
        fit_data,
        state_names=build_state_names(fit_data, CORE_STATE_NAMES),
        n_jobs=1,
    )
    return model, parent_map


def combine_models(
    core_model: BayesianNetwork,
    extra_models: Sequence[BayesianNetwork],
    core_columns: Sequence[str],
) -> BayesianNetwork:
    combined = BayesianNetwork(list(core_model.edges()))
    combined.add_nodes_from(core_columns)
    combined.add_cpds(*core_model.get_cpds())

    for model in extra_models:
        for parent, child in model.edges():
            if child not in core_columns:
                if child not in combined.nodes():
                    combined.add_node(child)
                if parent not in combined.nodes():
                    combined.add_node(parent)
                combined.add_edge(parent, child)

        for node in model.nodes():
            if node not in core_columns and node not in combined.nodes():
                combined.add_node(node)

        for cpd in model.get_cpds():
            if cpd.variable not in core_columns:
                combined.add_cpds(cpd)

    combined.check_model()
    return combined


def normalize(probabilities: np.ndarray) -> np.ndarray:
    probs = probabilities.astype(float)
    total = probs.sum()
    if total <= 0 or not np.isfinite(total):
        return np.ones_like(probs) / len(probs)
    return probs / total


def build_sampling_lookup(model: BayesianNetwork) -> Dict[str, Dict[str, object]]:
    lookup: Dict[str, Dict[str, object]] = {}

    for node in nx.topological_sort(model):
        cpd = model.get_cpds(node)
        parents = list(cpd.variables[1:])
        states = list(cpd.state_names[node])

        if not parents:
            probabilities = np.asarray(cpd.values, dtype=float).reshape(-1)
            lookup[node] = {
                "parents": parents,
                "states": states,
                "table": normalize(probabilities),
            }
            continue

        parent_state_lists = [list(cpd.state_names[parent]) for parent in parents]
        table: Dict[Tuple[int, ...], np.ndarray] = {}

        for combination in itertools.product(*parent_state_lists):
            context = dict(zip(parents, combination))
            probs = np.array(
                [cpd.get_value(**{node: state, **context}) for state in states],
                dtype=float,
            )
            table[tuple(int(v) for v in combination)] = normalize(probs)

        lookup[node] = {
            "parents": parents,
            "states": [int(state) for state in states],
            "table": table,
        }

    return lookup


def forward_sample(model: BayesianNetwork, size: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    order = list(nx.topological_sort(model))
    lookup = build_sampling_lookup(model)
    records: List[Dict[str, int]] = []

    for _ in range(size):
        row: Dict[str, int] = {}
        for node in order:
            node_info = lookup[node]
            parents = node_info["parents"]  # type: ignore[assignment]
            states = node_info["states"]  # type: ignore[assignment]

            if not parents:
                probabilities = node_info["table"]  # type: ignore[assignment]
            else:
                key = tuple(row[parent] for parent in parents)
                probabilities = node_info["table"][key]  # type: ignore[index]

            sampled = rng.choice(states, p=probabilities)
            row[node] = int(sampled)

        records.append(row)

    return pd.DataFrame.from_records(records, columns=order)


def forward_sample_with_evidence(
    model: BayesianNetwork,
    evidence: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    order = list(nx.topological_sort(model))
    lookup = build_sampling_lookup(model)
    records: List[Dict[str, int]] = []

    for evidence_row in evidence.to_dict(orient="records"):
        row = {key: int(value) for key, value in evidence_row.items()}
        for node in order:
            if node in row:
                continue

            node_info = lookup[node]
            parents = node_info["parents"]  # type: ignore[assignment]
            states = node_info["states"]  # type: ignore[assignment]

            if not parents:
                probabilities = node_info["table"]  # type: ignore[assignment]
            else:
                key = tuple(row[parent] for parent in parents)
                probabilities = node_info["table"][key]  # type: ignore[index]

            sampled = rng.choice(states, p=probabilities)
            row[node] = int(sampled)

        records.append(row)

    return pd.DataFrame.from_records(records, columns=order)


def save_model(model: BayesianNetwork, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / filename
    writer = BIFWriter(model)
    writer.write_bif(str(model_path))
    return model_path


def save_metadata(
    output_dir: Path,
    core_model: BayesianNetwork,
    parent_maps: Dict[str, Dict[str, List[str]]],
    findex_present_doc_vars: Sequence[str],
    findex_missing_doc_vars: Sequence[str],
    frames: Dict[str, pd.DataFrame],
    sample_summaries: Sequence[Dict[str, int]],
) -> Path:
    metadata = {
        "core_columns": CORE_COLUMNS,
        "core_edges": [list(edge) for edge in core_model.edges()],
        "dataset_shapes": {name: list(frame.shape) for name, frame in frames.items()},
        "dataset_parent_maps": parent_maps,
        "findex_doc_variables_present": list(findex_present_doc_vars),
        "findex_doc_variables_missing_from_csv": list(findex_missing_doc_vars),
        "sample_summaries": list(sample_summaries),
    }

    metadata_path = output_dir / "egypt_learned_model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata_path


def build_person_output(sample: pd.DataFrame) -> pd.DataFrame:
    persons = sample.copy()
    persons.insert(0, "synthetic_person_id", np.arange(1, len(persons) + 1))
    return persons


def build_sme_output(
    person_sample: pd.DataFrame,
    sme_model: BayesianNetwork,
    sme_extra_columns: Sequence[str],
    seed: int,
) -> pd.DataFrame:
    manager_rows = person_sample.loc[
        person_sample["elmps_num_enterprises_managed"] > 0,
        ["synthetic_person_id", *CORE_COLUMNS, "elmps_num_enterprises_managed"],
    ].copy()

    if manager_rows.empty:
        return pd.DataFrame(
            columns=[
                "synthetic_sme_id",
                "synthetic_manager_id",
                "manager_enterprise_sequence",
                *[f"manager_{column}" for column in CORE_COLUMNS],
                *sme_extra_columns,
            ]
        )

    evidence_rows: List[Dict[str, int]] = []
    linkage_rows: List[Dict[str, int]] = []

    for manager in manager_rows.to_dict(orient="records"):
        enterprise_count = int(manager["elmps_num_enterprises_managed"])
        for enterprise_index in range(enterprise_count):
            evidence_rows.append({column: int(manager[column]) for column in CORE_COLUMNS})
            linkage_rows.append(
                {
                    "synthetic_manager_id": int(manager["synthetic_person_id"]),
                    "manager_enterprise_sequence": enterprise_index + 1,
                    **{f"manager_{column}": int(manager[column]) for column in CORE_COLUMNS},
                }
            )

    enterprise_sample = forward_sample_with_evidence(
        sme_model,
        pd.DataFrame.from_records(evidence_rows, columns=CORE_COLUMNS),
        seed=seed,
    )

    smes = pd.DataFrame.from_records(linkage_rows)
    smes.insert(0, "synthetic_sme_id", np.arange(1, len(smes) + 1))
    for column in sme_extra_columns:
        smes[column] = enterprise_sample[column].astype(int)
    return smes


@lru_cache(maxsize=1)
def load_findex_grouped_descriptions() -> Dict[str, str]:
    descriptions: Dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z][A-Za-z0-9_]+)(?:\s+\([^)]+\))?\s+[–-]\s+(.+)$")

    for line in read_docx_lines(FINDEX_GROUPED_DOCX):
        match = pattern.match(line)
        if match:
            description = match.group(2).strip().rstrip(".")
            description = description.replace("â€œ", "\"").replace("â€", "\"").replace("â€‹", "")
            descriptions[match.group(1)] = description

    return descriptions


def schema_column_description(column: str) -> str:
    findex_overrides = {
        "fin17f": "Saved in some other way, such as through a person outside the household.",
        "fin26a": "Used a mobile phone or computer to make a bill payment in the past 12 months.",
        "fin26b": "Used a mobile phone or computer to buy something online that was delivered.",
    }
    core_descriptions = {
        "sex": "Sex of the individual, coded as 0 = male and 1 = female.",
        "age_band": "Age band of the individual: 15-24, 25-34, 35-44, 45-54, 55-64, or 65+.",
        "education_level": "Collapsed education level: low, secondary, post-secondary, or university+.",
        "urban_rural": "Settlement type, coded as 0 = urban and 1 = rural.",
        "in_workforce": "Labor-force participation, coded as 1 = in workforce and 0 = out of workforce.",
    }
    lfs_descriptions = {
        "lfs_region": "Governorate / region code from the LFS sample.",
        "lfs_marital_status": "Marital status category from LFS.",
        "lfs_employment_status": "Employment status in LFS: employee, employer, self-employed, unpaid family worker, or similar.",
        "lfs_occupation_group": "Main-job occupation group from LFS.",
        "lfs_industry_group": "Main-job industry group from LFS.",
        "lfs_sector": "Institutional sector of employment: government, public, private, joint/cooperative, foreign, or other.",
        "lfs_workplace_type": "Type of workplace such as home, separate premises, street, transport, construction site, or agricultural land.",
        "lfs_job_stability": "Job stability category such as regular, temporary, part-time, or seasonal.",
        "lfs_contract_type": "Type of employment contract, including official, written, verbal, or none.",
        "lfs_health_insurance": "Whether the job provides health insurance coverage.",
        "lfs_social_security": "Whether the job provides social security coverage.",
        "lfs_works_in_establishment": "Whether the individual works in an establishment rather than in dispersed or informal settings.",
        "lfs_establishment_size_band": "Establishment size band from the LFS enterprise-size variable.",
        "lfs_has_secondary_job": "Whether the individual has a secondary job.",
        "lfs_weekly_hours_band": "Quantile band of usual weekly hours worked in the main job.",
        "lfs_monthly_wage_band": "Quantile band of monthly wage from the main job.",
        "lfs_employer_income_band": "Quantile band of monthly employer income.",
        "lfs_self_employed_income_band": "Quantile band of monthly self-employment income.",
    }
    elmps_descriptions = {
        "elmps_employment_status": "Employment status in ELMPS: wage employee, employer, self-employed, or unpaid family worker.",
        "elmps_job_formality": "Formality of the main job, coded from the ELMPS formal / informal indicator.",
        "elmps_firm_size_band": "Firm-size band of the main job in ELMPS.",
        "elmps_social_insurance_job": "Whether the main job provides social insurance.",
        "elmps_has_job_contract": "Whether the individual has a job contract in the main job.",
        "elmps_medical_insurance_job": "Whether the main job provides medical insurance.",
        "elmps_paid_leave_job": "Whether the main job includes paid leave.",
        "elmps_paid_sick_leave_job": "Whether the main job includes paid sick leave.",
        "elmps_has_secondary_job": "Whether the individual has a second job in ELMPS.",
        "elmps_owns_mobile_phone": "Whether the individual owns a mobile phone.",
        "elmps_has_mobile_wallet": "Whether the individual has a mobile wallet or mobile-money account.",
        "elmps_has_any_savings": "Whether the individual has any savings.",
        "elmps_savings_method": "Main savings channel used by the individual.",
        "elmps_savings_interest_bearing": "Whether the person's savings are interest-bearing.",
        "elmps_applied_formal_loan_last12m": "Whether the individual applied for a formal loan in the past 12 months.",
        "elmps_formal_loan_outcome": "Outcome of the formal loan application: approved, rejected, pending, or unknown.",
        "elmps_formal_lender_type": "Type of formal lender approached for the loan.",
        "elmps_formal_loan_purpose": "Purpose of the formal loan, including enterprise, consumption, housing, health, education, or debt needs.",
        "elmps_formal_loan_cost_type": "Type of cost attached to the formal loan, such as interest, fees, both, or none.",
        "elmps_borrowed_from_individuals_last12m": "Whether the individual borrowed informally from other people in the past 12 months.",
        "elmps_amount_borrowed_from_individuals_band": "Quantile band of the amount borrowed from individuals.",
        "elmps_informal_loan_cost_type": "Type of cost attached to the informal loan.",
        "elmps_has_bank_account": "Whether the individual has a bank account.",
        "elmps_bank_savings_amount_band": "Quantile band of the amount saved in bank accounts.",
        "elmps_num_enterprises_managed": "Number of SMEs managed by the individual in the synthetic population.",
        "elmps_manages_sme": "Whether the individual manages at least one SME.",
    }
    sme_descriptions = {
        "sme_enterprise_activity_1digit": "Main enterprise activity code at the 1-digit level.",
        "sme_enterprise_age_band": "Enterprise age band derived from the year the business was established.",
        "sme_ownership_structure": "Ownership structure of the enterprise, such as household-only or with outside partners.",
        "sme_household_ownership_share_band": "Quantile band of the household ownership share in the enterprise.",
        "sme_workplace_type": "Type of workplace used by the enterprise, such as home, shop, workshop, kiosk, taxi, field, or online.",
        "sme_current_capital_band": "Current capital band of the enterprise.",
        "sme_startup_capital_band": "Startup capital band of the enterprise when it began.",
        "sme_startup_capital_source": "Main source of startup capital for the enterprise.",
        "sme_primary_buyer_type": "Main buyer category for the enterprise's goods or services.",
        "sme_has_business_license": "Whether the enterprise has a business license.",
        "sme_has_commercial_registration": "Whether the enterprise has commercial registration.",
        "sme_keeps_accounting_books": "Whether the enterprise keeps regular accounting books.",
        "sme_has_online_page_or_storefront": "Whether the enterprise has an online page, social-media page, or electronic storefront.",
        "sme_has_mobile_sales_app": "Whether the enterprise uses a mobile app to display or sell products or services.",
        "sme_share_of_sales_online_band": "Quantile band of the share of sales made through online channels.",
        "sme_hires_nonhousehold_workers": "Whether the enterprise hires workers from outside the household.",
        "sme_num_nonhousehold_workers_band": "Quantile band of the number of non-household workers hired by the enterprise.",
        "sme_num_related_external_workers_band": "Quantile band of the number of hired workers who are relatives.",
        "sme_any_workers_with_social_insurance": "Whether any enterprise workers are covered by social insurance.",
        "sme_num_workers_with_social_insurance_band": "Quantile band of the number of workers with social insurance.",
        "sme_new_workers_joined_last12m": "Whether new workers joined the enterprise during the last 12 months.",
        "sme_workers_left_last12m": "Whether any workers left the enterprise during the last 12 months.",
        "sme_annual_wage_bill_band": "Quantile band of annual spending on workers' wages.",
        "sme_annual_taxes_paid_band": "Quantile band of annual taxes paid by the enterprise.",
        "sme_average_monthly_net_earnings_band": "Quantile band of the enterprise's average monthly net earnings.",
    }

    if column == "synthetic_person_id":
        return "Stable synthetic individual identifier."
    if column == "synthetic_sme_id":
        return "Stable synthetic SME identifier."
    if column == "synthetic_manager_id":
        return "Identifier of the linked synthetic person managing the SME."
    if column == "manager_enterprise_sequence":
        return "Sequence number of the SME within the manager's set of enterprises."
    if column.startswith("manager_"):
        manager_field = column.removeprefix("manager_")
        manager_descriptions = {
            "sex": "Sex of the SME manager, coded as 0 = male and 1 = female.",
            "age_band": "Age band of the SME manager: 15-24, 25-34, 35-44, 45-54, 55-64, or 65+.",
            "education_level": "Collapsed education level of the SME manager: low, secondary, post-secondary, or university+.",
            "urban_rural": "Settlement type of the SME manager, coded as 0 = urban and 1 = rural.",
            "in_workforce": "Labor-force participation status of the SME manager, coded as 1 = in workforce and 0 = out of workforce.",
        }
        return manager_descriptions.get(
            manager_field,
            "Core attribute of the linked SME manager.",
        )
    if column in core_descriptions:
        return core_descriptions[column]
    if column.startswith("findex_"):
        raw_name = column.removeprefix("findex_")
        if raw_name in findex_overrides:
            return findex_overrides[raw_name]
        findex_descriptions = load_findex_grouped_descriptions()
        if raw_name in findex_descriptions:
            return findex_descriptions[raw_name] + "."
    if column in lfs_descriptions:
        return lfs_descriptions[column]
    if column in elmps_descriptions:
        return elmps_descriptions[column]
    if column in sme_descriptions:
        return sme_descriptions[column]
    return column.replace("_", " ").capitalize() + "."


def save_population_schema(
    output_path: Path,
    person_columns: Sequence[str],
    sme_columns: Sequence[str],
    sample_summaries: Sequence[Dict[str, int]],
) -> Path:
    lines = [
        "# Egypt Synthetic Population Schema",
        "",
        "## Scope",
        "",
        "This synthetic population contains two linked entity tables:",
        "",
        "- `persons`: synthetic individuals sampled from the learned LFS-FINDEX-ELMPS person network.",
        "- `smes`: synthetic household non-farm enterprises sampled from the learned ELMPS enterprise network and linked to synthetic managers in `persons`.",
        "",
        "The requested sample sizes refer to the number of synthetic persons. The number of SMEs is endogenous and is generated from the sampled person-level variable `elmps_num_enterprises_managed`.",
        "",
        "## Output Runs",
        "",
        "| Persons requested | Synthetic persons | Synthetic SMEs |",
        "| --- | --- | --- |",
    ]

    for summary in sample_summaries:
        lines.append(
            f"| {summary['requested_persons']} | {summary['synthetic_persons']} | {summary['synthetic_smes']} |"
        )

    lines.extend(
        [
            "",
            "## Persons Table",
            "",
            "| Column | Description |",
            "| --- | --- |",
        ]
    )
    for column in person_columns:
        description = schema_column_description(column)
        lines.append(f"| `{column}` | {description} |")

    lines.extend(
        [
            "",
            "## SMEs Table",
            "",
            "| Column | Description |",
            "| --- | --- |",
        ]
    )
    for column in sme_columns:
        description = schema_column_description(column)
        lines.append(f"| `{column}` | {description} |")

    lines.extend(
        [
            "",
            "## Coding Notes",
            "",
            "- All modeled fields are discrete integer-coded variables.",
            "- `0` is used as a substantive category for some count and money bands where zero is meaningful.",
            "- `-1` denotes missing or structurally unavailable values after harmonization.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()

    print("Loading and harmonizing LFS 2024...")
    lfs_frame, lfs_extra_columns = preprocess_lfs()
    print(f"  LFS rows after harmonization: {len(lfs_frame):,}")

    print("Loading and harmonizing Global Findex 2025 Egypt extract...")
    findex_frame, findex_extra_columns, present_doc_vars, missing_doc_vars = preprocess_findex()
    print(f"  FINDEX rows after harmonization: {len(findex_frame):,}")
    print(f"  FINDEX grouped-doc variables present in CSV: {len(present_doc_vars)}")
    if missing_doc_vars:
        print(f"  FINDEX grouped-doc variables missing from CSV: {', '.join(missing_doc_vars)}")

    print("Loading and harmonizing ELMPS 2023 cross-section (part 1)...")
    elmps_frame, elmps_extra_columns = preprocess_elmps()
    print(f"  ELMPS rows after harmonization: {len(elmps_frame):,}")

    print("Loading and harmonizing ELMPS 2023 SMEs...")
    sme_frame, sme_extra_columns = preprocess_smes()
    print(f"  ELMPS SME rows after harmonization: {len(sme_frame):,}")

    print("Learning LFS core Bayesian network...")
    core_model = learn_core_model(lfs_frame[CORE_COLUMNS], max_indegree=args.max_core_indegree)
    print(f"  Learned core edges: {list(core_model.edges())}")

    print("Learning LFS enrichment distributions...")
    lfs_model, lfs_parent_map = learn_dataset_enrichment_model(
        lfs_frame,
        CORE_COLUMNS,
        lfs_extra_columns,
        core_model.edges(),
        max_extra_parents=args.max_extra_parents,
    )

    print("Learning FINDEX enrichment distributions...")
    findex_model, findex_parent_map = learn_dataset_enrichment_model(
        findex_frame,
        CORE_COLUMNS,
        findex_extra_columns,
        core_model.edges(),
        max_extra_parents=args.max_extra_parents,
    )

    print("Learning ELMPS enrichment distributions...")
    elmps_model, elmps_parent_map = learn_dataset_enrichment_model(
        elmps_frame,
        CORE_COLUMNS,
        elmps_extra_columns,
        core_model.edges(),
        max_extra_parents=args.max_extra_parents,
    )

    print("Learning SME enrichment distributions...")
    sme_model, sme_parent_map = learn_dataset_enrichment_model(
        sme_frame,
        CORE_COLUMNS,
        sme_extra_columns,
        core_model.edges(),
        max_extra_parents=args.max_extra_parents,
    )

    print("Combining models...")
    person_model = combine_models(
        core_model,
        [lfs_model, findex_model, elmps_model],
        CORE_COLUMNS,
    )
    sme_combined_model = combine_models(core_model, [sme_model], CORE_COLUMNS)

    person_model_path = save_model(person_model, OUTPUT_DIR, "egypt_person_learned_model.bif")
    sme_model_path = save_model(sme_combined_model, OUTPUT_DIR, "egypt_sme_learned_model.bif")
    print(f"  Saved person model to {person_model_path}")
    print(f"  Saved SME model to {sme_model_path}")

    if not args.skip_sample:
        sample_summaries: List[Dict[str, int]] = []
        latest_person_columns: List[str] = []
        latest_sme_columns: List[str] = []

        for offset, size in enumerate(args.sample_sizes):
            print(f"Drawing {size:,} synthetic person records...")
            person_sample = build_person_output(
                forward_sample(person_model, size=size, seed=args.seed + offset)
            )
            person_path = OUTPUT_DIR / f"egypt_synthetic_persons_{size}.csv"
            person_sample.to_csv(person_path, index=False)

            print(f"Drawing linked synthetic SMEs for the {size:,}-person population...")
            sme_sample = build_sme_output(
                person_sample,
                sme_combined_model,
                sme_extra_columns,
                seed=args.seed + 1000 + offset,
            )
            sme_path = OUTPUT_DIR / f"egypt_synthetic_smes_{size}.csv"
            sme_sample.to_csv(sme_path, index=False)

            latest_person_columns = person_sample.columns.tolist()
            latest_sme_columns = sme_sample.columns.tolist()
            sample_summaries.append(
                {
                    "requested_persons": int(size),
                    "synthetic_persons": int(len(person_sample)),
                    "synthetic_smes": int(len(sme_sample)),
                }
            )
            print(f"  Saved persons to {person_path}")
            print(f"  Saved SMEs to {sme_path}")

        schema_path = save_population_schema(
            SCHEMA_DOC_PATH,
            latest_person_columns,
            latest_sme_columns,
            sample_summaries,
        )
        metadata_path = save_metadata(
            OUTPUT_DIR,
            core_model,
            {
                "lfs": lfs_parent_map,
                "findex": findex_parent_map,
                "elmps_person": elmps_parent_map,
                "elmps_sme": sme_parent_map,
            },
            present_doc_vars,
            missing_doc_vars,
            {
                "lfs": lfs_frame,
                "findex": findex_frame,
                "elmps_person": elmps_frame,
                "elmps_sme": sme_frame,
            },
            sample_summaries,
        )
        print(f"  Saved schema to {schema_path}")
        print(f"  Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
