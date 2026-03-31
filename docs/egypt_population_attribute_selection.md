# Egypt Synthetic Population: Initial Attribute Selection

## Scope

This note defines the initial variable shortlist for building a synthetic population for Egypt for simulation purposes. The target output is two linked synthetic entity sets:

1. `persons`: individuals with socio-demographic, employment, and financial-behavior attributes.
2. `smes`: household non-agricultural enterprises with formality, structural, and financial-behavior attributes.

The selection is designed for a Bayesian-network workflow similar to the approach described in the attached paper and the referenced population-synthesis repository: identify overlap variables, harmonize them, learn conditional structure from the richest source available for each block, and then sample a full synthetic population.

## Source Filters Applied

| Source | Raw file used | Filter applied | Result |
| --- | --- | --- | --- |
| Global Findex 2025 release | `DATA/FINDEX 2024/Findex_Microdata_2025_Egypt, Arab Rep..csv` | Keep Egypt only. The local file is already Egypt-only. | 1,001 individual records, all with `economy = Egypt, Arab Rep.` and `year = 2024`. For this project, treat this file as the Egypt extract from the Global Findex 2025 release package. |
| LFS 2024 | `DATA/LFS 2024/Egypt 2024-LFS STATA-V1.zip` -> `Egypt 2024-LFS IND-V1.dta` | No row filter at this stage. | 296,724 individual records. |
| ELMPS 2023 panel | `DATA/ELMPS 2023/elmps 2023 panel 98_23 v2.0.rar` -> `elmps 2023 panel 98_23 v2.0.dta` | Keep only the 2023 wave by selecting variables ending in `_23`. | 106,637 person records in wide panel format. |
| ELMPS 2023 cross-section | `DATA/ELMPS 2023/elmps 2023 xs v2.1 all.rar` -> `elmps 2023 xs v2.1 all.dta` | Use the 2023 raw individual finance and enterprise modules. | 70,636 records; enterprise fields are repeated blocks for up to 5 enterprises per household. |

## Important Data Notes

- The Findex local metadata identifies the study as `EGY_2024_FINDEX_v01_M`, while the PDF title refers to "The Global Findex Database 2025" because the documentation was generated on October 2, 2025. For this project, we treat it as the Global Findex 2025 Egypt release package.
- The helper note `DATA/FINDEX 2024/findex_variables_grouped.docx` still says "Egypt 2021 Microdata" in its title. Its grouped descriptions are useful, but the survey-year reference in that file is stale and should not override the CSV or PDF metadata.
- The ELMPS panel file is wide, not stacked. "Use only the most recent year" therefore means retaining only the `_23` variables from the panel file.
- The ELMPS enterprise module is stored in repeated wide blocks such as `q15114_1` ... `q15114_5`. Before modeling SMEs, this block should be reshaped to one row per enterprise with an explicit `enterprise_slot` from 1 to 5.

## Common Person-Level Anchors

These are the overlap variables that should anchor the first harmonization pass across datasets.

| Harmonized field | FINDEX 2024 | LFS 2024 | ELMPS 2023 | Notes |
| --- | --- | --- | --- | --- |
| `person_weight` | `wgt` | `pweight` | `expan_indiv_23`, `expan_indiv` | Keep all survey weights. |
| `sex` | `female` | `sex` | `sex_23` | Findex stores a female-coded binary; LFS and ELMPS use male/female labels directly. |
| `age_years` | `age` | `age` | `age_23` | Keep continuous age, then derive age bands consistently. |
| `education_level` | `educ` | `educ` | `educ_23` | Needs a common collapsed scheme because the three sources use different category counts. |
| `urban_rural` | `urbanicity` | `rururb` | `urban_23` | Standardize to `urban` / `rural`. |
| `in_workforce` | `emp_in` | `lfs` or `mas` | `crwrkst1_23` | Findex only distinguishes in-workforce vs not. |
| `employment_status` | limited | `emps` | `usempstp_23` | Only LFS and ELMPS support detailed labor-status harmonization. |
| `income_or_wealth_proxy` | `inc_q` | derived later from wages/income | `qwealth_23` | Not a strict common variable, but useful as a latent socioeconomic-status block. |
| `region` | not available | `reg` | `region_23` or `gov_23` | Use only for Egypt-internal calibration; Findex cannot support subnational matching directly. |

## Recommended Backbone by Entity

- `persons`: use `LFS 2024` as the main structural backbone because it is large and already harmonized for labor-market structure.
- `person_finance`: use `FINDEX 2024` for nationally calibrated financial-inclusion behavior, supplemented by `ELMPS 2023` finance-module variables where local linkage to labor or household context is needed.
- `smes`: use `ELMPS 2023` cross-sectional enterprise module after reshaping repeated enterprise blocks to long format.

## Selected FINDEX 2025 Bridge Variables

These are the Findex variables that directly bridge the person backbone to finance behavior in the first Bayesian-network version. The exhaustive retained Findex list appears in the next subsection.

| Source column | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `wgt` | `findex_weight` | Survey sampling weight. | Required for weighted distribution learning. |
| `female` | `sex` | 1 = Female, 2 = Male. | Common socio-demographic anchor. |
| `age` | `age_years` | Respondent age in years. | Common anchor. |
| `educ` | `education_3cat` | 1 = Primary or less, 2 = Secondary, 3 = Tertiary. | Common anchor and SES proxy. |
| `inc_q` | `income_quintile` | Within-country household income quintile, 1 to 5. | Main Findex socioeconomic proxy. |
| `emp_in` | `in_workforce` | 1 = In workforce, 2 = Out of workforce. | Only labor overlap available in Findex. |
| `urbanicity` | `urban_rural` | 1 = Rural, 2 = Urban. | Common settlement anchor. |
| `account_fin` | `has_formal_account` | Binary ownership of an account at a financial institution. | Core formal-inclusion variable. |
| `account_mob` | `has_mobile_money_account` | Binary ownership of a mobile money account. | Mobile-finance dimension. |
| `account` | `has_any_account` | Binary ownership of any account. | High-level financial-access variable. |
| `dig_account` | `has_digitally_enabled_account` | Binary indicator for an account usable for digital payments. | Important for digital-finance simulations. |
| `borrowed` | `borrowed_last_12m` | Binary indicator that the person borrowed in the last 12 months. | Core credit behavior. |
| `saved` | `saved_last_12m` | Binary indicator that the person saved in the last 12 months. | Core savings behavior. |
| `merchantpay_dig` | `digital_merchant_payment` | Binary digital merchant payment indicator. | Measures active digital use, not just access. |
| `anydigpayment` | `any_digital_payment` | Binary indicator for any digital payment sent or received. | Good summary adoption variable. |
| `internet_use` | `internet_use_last_3m` | Binary internet-use indicator. | Key digital-enablement covariate. |
| `fin17a` | `saved_formally` | Saved at a bank or similar formal financial institution. | Distinguishes formal saving from general saving. |
| `fin22a` | `borrowed_formally` | Borrowed from a formal financial institution. Original responses should be collapsed to yes vs non-yes. | Core formal-credit variable. |
| `fin22b` | `borrowed_from_family_friends` | Borrowed from family or friends. Original responses should be collapsed to yes vs non-yes. | Captures informal-credit channel. |
| `fin22e` | `borrowed_for_business` | Borrowed to start or operate a business. Original responses should be collapsed to yes vs non-yes. | Important for SME-owner financial behavior. |
| `fin31a` | `utilities_paid_from_account` | Conditional binary among utility payers: paid utility bills using a bank account. | Channel-specific payment behavior. |
| `fin31b` | `utilities_paid_by_mobile` | Conditional binary among utility payers: paid utility bills using a mobile phone. | Digital-payment channel. |
| `fin34a` | `wages_paid_into_account` | Conditional binary among wage receivers: employer paid wages into an account. | Direct link between labor and finance. |
| `fin34b` | `wages_paid_by_mobile` | Conditional binary among wage receivers: employer paid wages through mobile phone. | Digital wage channel. |
| `fin34c` | `wages_paid_in_cash` | Conditional binary among wage receivers: employer paid wages in cash. | Important benchmark against formal channels. |

### FINDEX Variables Deliberately Not Prioritized

- `receive_wages`, `receive_transfers`, `receive_pensions`, `pay_utilities`, and similar summary variables are useful descriptively, but the underlying channel-specific items are better for synthesis because they are easier to binarize and condition on the proper survey universe.
- Open-ended or economy-specific barrier variables can be added later if the first BN version needs a separate "reasons for exclusion" block.

## Exhaustive FINDEX 2025 Financial And Barrier Variables To Retain

The full model should retain every Findex variable listed in `DATA/FINDEX 2024/findex_variables_grouped.docx` that is physically present in the Egypt CSV extract. In `model.py`, these should be loaded as dataset-specific enrichment variables, typically with a `findex_` prefix to avoid name clashes with harmonized core fields.

### FINDEX Variables Present In The Egypt CSV

- Survey / socio-demographic anchors: `female`, `age`, `educ`, `inc_q`, `emp_in`, `urbanicity`.
- Ownership summary indicators: `account_fin`, `account_mob`, `account`, `dig_account`.
- Ownership micro-questions: `fin2`, `fin10`, `fin11_0`, `fin11_1`, `fin11_2`.
- Saving history: `saved`, `fin17a`, `fin17b`, `fin17c`, `fin17e`, `fin17f`, `fin18`.
- Insurance history: `fin19`.
- Credit and borrowing history: `borrowed`, `fin20`, `fin21`, `fin22a`, `fin22a_1`, `fin22b`, `fin22c`, `fin22d`, `fin22e`, `fin22f`, `fin22g`, `fin22h`, `fin23`.
- Employment and wage receipt: `receive_wages`, `fin32`, `fin33`, `fin34a`, `fin34b`, `fin34c`, `fin34d`, `fin35`, `fin36`, `fin36a`.
- Utility bill payments: `pay_utilities`, `fin30`, `fin31a`, `fin31b`, `fin31c`, `fin31d`.
- Remittances: `domestic_remittances`, `fh1`, `fin28`, `fh2`, `fin29`, `fh2a`.
- Government transfers, pensions, and agricultural receipts: `receive_transfers`, `receive_pensions`, `receive_agriculture`, `fin37`, `fin38`, `fin39a`, `fin39b`, `fin39c`, `fin39d`.
- Account-use and action variables: `fin5`, `fin6`, `fin7`, `fin8`, `fin9a`, `fin9b`.
- Digital payment and e-commerce behavior: `merchantpay_dig`, `anydigpayment`, `fin3`, `fin26a`, `fin26b`, `fin27`.
- Barriers and perceptions present in the Egypt CSV: `fin11a`, `fin11b`, `fin11c`, `fin11d`, `fin11e`, `fin11f`.

### FINDEX Variables Listed In The Grouped Docx But Missing From The Local Egypt CSV

- `fin1`
- `fin25e_1`
- `fin25e_2`
- `fin25e_3`
- `fin25e_4`
- `fin11g`
- `fin11h`
- `fin11i`
- `fin11j`

These grouped-doc variables are not present in `Findex_Microdata_2025_Egypt, Arab Rep..csv`, so they cannot be modeled unless another Egypt Findex extract containing them is added to the workspace.

## Selected LFS 2024 Person Variables

The LFS file should carry the main structural labor-market population.

| Source column | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `pweight` | `lfs_weight` | Individual survey weight. | Required for weighted synthesis. |
| `reg` | `governorate` | Governorate code. | Enables Egypt-internal geographic heterogeneity. |
| `rururb` | `urban_rural` | 0 = Rural, 1 = Urban. | Common anchor. |
| `age` | `age_years` | Age in years. | Common anchor. |
| `sex` | `sex` | 1 = Male, 2 = Female. | Common anchor. |
| `mart` | `marital_status` | Standardized marital-status categories. | Important household/labor correlate. |
| `educ` | `education_level` | Standardized education categories from none to postgraduate. | Common anchor and labor predictor. |
| `lfs` | `labor_force_status` | Active / inactive. | Common labor anchor. |
| `mas` | `main_activity_status` | Employed, unemployed, homemaker, student, retired/disabled, other. | Better labor detail than Findex. |
| `emps` | `employment_status` | Employee, employer, self-employed, unpaid family worker, etc. | Critical for linking to SME ownership and informality. |
| `occ_08` | `occupation_1digit` | Main-job occupation, ISCO-08 1-digit. | Core labor-structure variable. |
| `ind` | `industry_1digit` | Main-job industry, standardized 1-digit sector. | Core labor-structure variable. |
| `sector` | `institutional_sector` | Government, public, private, joint/cooperative, foreign, other. | Distinguishes public vs private labor market. |
| `wrkplc` | `workplace_type` | Home, separate premises, street vending, transport, construction site, agricultural land, etc. | Useful proxy for enterprise type and informality. |
| `empstab` | `job_stability` | Full-time/regular, part-time/temporary, seasonal/irregular. | Important precariousness dimension. |
| `empcont` | `employment_contract` | Official, written unlimited, written limited, verbal, none, etc. | Strong formality indicator. |
| `hlthins` | `health_insurance` | Binary health-insurance coverage. | Employment-benefit/formality block. |
| `socsec` | `social_security` | Binary social-security coverage. | Main formalization signal. |
| `estab` | `works_in_establishment` | Binary indicator. | Distinguishes establishment-based work from informal/home-based work. |
| `numwrk` | `establishment_size_band` | Firm-size bands from 1-4 up to 100+. | Key SME-size covariate. |
| `hrswk` | `weekly_hours_main_job` | Weekly hours in main job. | Continuous labor-intensity variable. |
| `totwag` | `monthly_wage_main_job` | Monthly wage from regular main job. | Main earnings measure for wage workers. |
| `empinc` | `monthly_income_employer` | Monthly income for employers. | Required if backbone includes employers. |
| `sempinc` | `monthly_income_self_employed` | Monthly income for self-employed workers. | Required for own-account activity. |
| `secjob` | `has_secondary_job` | Binary indicator. | Useful for multi-job households and income diversification. |

## Selected ELMPS 2023 Person Variables From the Panel File

Use these only from the `_23` wave fields in `elmps 2023 panel 98_23 v2.0.dta`.

| Source column | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `expan_indiv_23` | `elmps_person_weight` | Individual survey weight. | Required for weighted synthesis. |
| `region_23` | `region_6cat` | Greater Cairo, Alexandria/Suez Canal, urban lower, urban upper, rural lower, rural upper. | Good geographic aggregation for Egypt. |
| `urban_23` | `urban_rural` | 1 = Urban, 2 = Rural. | Common anchor. |
| `age_23` | `age_years` | Age in years. | Common anchor. |
| `sex_23` | `sex` | 1 = Male, 2 = Female. | Common anchor. |
| `marital_23` | `marital_status` | Less than minimum age, never married, contractually married, married, divorced, widowed. | Household and labor correlate. |
| `hhsize_23` | `household_size` | Number of household members. | Useful for joint person-household modeling. |
| `qwealth_23` | `wealth_quintile` | Household wealth quintile. | SES proxy complementary to Findex income quintile. |
| `educ_23` | `education_level_7cat` | Illiterate through postgraduate. | Common anchor and SES predictor. |
| `yrschl_23` | `years_schooling` | Years of schooling. | Continuous education measure. |
| `crwrkst1_23` | `current_work_status` | Employed, unemployed, out of labor force. | Clean labor-force anchor. |
| `usempstp_23` | `employment_status` | Waged employee, employer, self-employed, unpaid family worker. | Direct bridge to SME roles. |
| `usformal_23` | `job_formality` | 1 = Formal, 0 = Informal. | Main local formality variable. |
| `usfirm_size_23` | `firm_size_band` | 1-4, 5-9, 10-24, 25-49, 50-99, 100+, don't know. | Key employment-context variable. |
| `ussocinsp_23` | `social_insurance_job` | Yes / No / Don't know. | Formal employment signal. |
| `uscontrp_23` | `has_job_contract` | Yes / No / Don't know. | Formal employment signal. |
| `usmedins_23` | `medical_insurance_job` | Job-linked medical insurance. | Benefit/formality dimension. |
| `uspdleave_23` | `paid_leave_job` | Paid leave from primary job. | Employment-quality dimension. |
| `uspdsick_23` | `paid_sick_leave_job` | Paid sick leave from primary job. | Employment-quality dimension. |
| `ushrswk1_23` | `usual_weekly_hours` | Usual weekly hours of market work. | Continuous labor-intensity variable. |
| `mnthwg_23` | `monthly_wage` | Monthly wage from primary job. | Earnings block. |
| `hrwg_23` | `hourly_wage` | Hourly wage in primary job. | Useful for consistency checks and calibration. |
| `scjob_23` | `has_secondary_job` | Incidence of secondary job. | Income diversification. |
| `unionont_23` | `trade_union_member` | Union membership. | Formal labor-market correlate. |
| `fament_23` | `household_has_family_enterprise` | Whether the household has a family enterprise. | Natural bridge from persons to SME module. |
| `lglstsco_23` | `company_legal_status` | Individual project, company of individuals, joint stock, limited liability, foreign branch, other. | Useful when modeling employers and owner-manager types. |

## Selected ELMPS 2023 Individual Finance Variables From the Raw Cross-Section

These variables are needed because the harmonized panel file does not carry the detailed 2023 finance module.

| Source column | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `expan_indiv` | `elmps_raw_person_weight` | Individual survey weight in the raw 2023 cross-section. | Use when learning finance-module distributions from the raw file. |
| `q12102` | `owns_mobile_phone` | Yes / No mobile-phone ownership. | Digital-enablement anchor. |
| `q12104` | `has_mobile_wallet` | Yes / No mobile-money wallet. | Local mobile-finance variable. |
| `q12201` | `has_any_savings` | Yes / No. | Core savings indicator. |
| `q12202` | `savings_method` | Post office, Nasser Social Bank, other public bank, private bank, cash, gold, jewelry, land/real estate, car, tuk-tuk, broker, smartphone, other. | Rich local savings-channel variable. |
| `q12203` | `savings_interest_bearing` | Yes / No / Don't know. | Distinguishes formal interest-bearing saving. |
| `q12204` | `applied_formal_loan_last12m` | Yes / No. | Formal credit demand. |
| `q12205` | `formal_loan_outcome` | Successful, unsuccessful, pending, don't know. | Formal credit access outcome. |
| `q12207` | `formal_lender_type` | Nasser Social Bank, Agriculture Credit Bank, public bank, private bank, NGO, private company, etc. | Identifies lender channel. |
| `q12208` | `formal_loan_purpose` | Non-farm enterprise, agricultural enterprise, car, marriage, education, house, medical emergency, debt repayment, house expenses, and other local purposes. | Critical for linking borrowing to enterprise and household shocks. |
| `q12210` | `formal_loan_cost_type` | Interest, fees, both, none, don't know. | Describes borrowing terms. |
| `q12213` | `borrowed_from_individuals_last12m` | Yes / No / Don't know. | Informal credit channel. |
| `q12216` | `amount_borrowed_from_individuals` | Amount borrowed from individuals. | Useful if a continuous informal-credit measure is needed later. |
| `q12217` | `informal_loan_cost_type` | Interest, fees, both, none, don't know. | Informal borrowing terms. |
| `q12229` | `has_bank_account` | Yes / No. | Formal account-ownership variable from a local survey. |
| `q12230` | `bank_savings_amount` | Amount saved in bank accounts. | Continuous savings intensity measure. |

## Selected ELMPS 2023 SME Variables From the Raw Enterprise Module

The enterprise module captures household non-agricultural enterprises. These fields should be reshaped from wide to long using `enterprise_slot = 1..5`.

### SME Identifiers And Reshape Logic

| Source columns | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `hhid`, `indid`, `pn` | `household_id`, `person_id`, `person_number` | Household and person identifiers from the raw file. | Needed to link SMEs back to persons and households. |
| `expan_hh` | `elmps_household_weight` | Household weight. | Use for household-enterprise totals. |
| `q15101` | `household_has_nonfarm_enterprise` | Any household member owns/manages/works in a non-agricultural enterprise. | Entry point for the SME universe. |
| `q15102` | `num_household_enterprises` | Number of household enterprises. | Determines how many enterprise slots to keep after reshape. |
| `q15405_[1-5]` | `enterprise_manager_person_number` | Household member managing day-to-day business activities. | Main link from enterprise to person layer. |

### SME Structural And Formality Variables

| Source columns | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `q15106_[1-5]` | `enterprise_start_year_or_date` | When the enterprise was established. | Enterprise age / vintage. |
| `q15107_[1-5]` | `ownership_structure` | Household alone vs household with outside partners. | Ownership block. |
| `q15108_[1-5]` | `household_ownership_share_pct` | Percent owned by the household. | Useful for mixed-ownership cases. |
| `q15109_[1-5]` | `enterprise_workplace_type` | Home, shop/restaurant, office/apartment, workshop/factory, kiosk, mobile workplace, taxi, field/farm, online, etc. | Strong predictor of informality and scale. |
| `q15104_1_[1-5]`, `q15104_2_[1-5]`, `q15104_3_[1-5]`, `q15104_4_[1-5]` | `enterprise_activity_code` | Enterprise activity code stored at 1-, 2-, 3-, and 4-digit levels. | Needed for sector/industry synthesis. |
| `q15110_[1-5]` | `current_capital_band` | Current capital value band from none to LE 50,000+. | Scale proxy. |
| `q15111_[1-5]` | `startup_capital_value` | Estimated capital value when the project first started. | Entry-scale proxy. |
| `q15112_[1-5]` | `startup_capital_source` | Household savings, inheritance, relatives/friends, ROSCA, remittances, farm proceeds, non-farm enterprise proceeds, NGO/public/private bank loans, money lenders, grant, etc. | Main SME finance-origin variable. |
| `q15113_[1-5]` | `primary_buyer_type` | Consumers, small firms, large firms, public sector, government, wholesalers, retailers, exporters, tourists, NGOs, etc. | Demand-side market orientation. |
| `q15114_[1-5]` | `has_business_license` | Yes / No / N/A. | Main formality indicator. |
| `q15115_[1-5]` | `has_commercial_registration` | Yes / No / N/A. | Main formality indicator. |
| `q15116_[1-5]` | `keeps_accounting_books` | Yes / No / N/A. | Management-formality proxy. |

### SME Digital And Sales Variables

| Source columns | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `q15117_[1-5]` | `has_online_page_or_storefront` | Page on internet, social media, or electronic platform. | Digital-market presence. |
| `q15118_[1-5]` | `has_mobile_sales_app` | Mobile application to display or sell goods/services. | Digital-sales capability. |
| `q15120_[1-5]` | `share_of_sales_online_pct` | Percentage of sales achieved via internet/social/electronic channels. | Measures digital commercialization depth. |

### SME Labor And Employment Variables

| Source columns | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `q15201_[1-5]` | `hires_nonhousehold_workers` | Whether the enterprise hires workers from outside the household. | Distinguishes own-account/family enterprise from employer SME. |
| `q15202_[1-5]` | `num_nonhousehold_workers` | Number of workers currently hired from outside the household. | Main SME size measure. |
| `q15202_1_[1-5]` | `num_related_external_workers` | Number of hired workers who are relatives. | Helpful for family-business structure. |
| `q15203_[1-5]` | `any_workers_with_social_insurance` | Whether any workers have social insurance. | Enterprise-level formality signal. |
| `q15204_[1-5]` | `num_workers_with_social_insurance` | Number of workers covered by social insurance. | Intensity of formality. |
| `q15205_[1-5]` | `new_workers_joined_last12m` | Worker inflow during the past 12 months. | SME growth/dynamics. |
| `q15207_[1-5]` | `workers_left_last12m` | Worker outflow during the past 12 months. | SME turnover/dynamics. |

### SME Financial Performance Variables

| Source columns | Harmonized field | Meaning / coding | Why keep it |
| --- | --- | --- | --- |
| `q15304_1_[1-5]` | `annual_wage_bill` | Amount spent on workers' wages during the past 12 months. | Core labor-cost variable. |
| `q15304_13_[1-5]` | `annual_taxes_paid` | Amount spent on taxes during the past 12 months. | Fiscal-formality and cost variable. |
| `q15401_[1-5]` | `average_monthly_net_earnings` | Average enterprise net earnings per month. | Main SME income / profitability proxy. |

## Minimum First-Pass Harmonization Rules

These transformations should be applied before model training.

| Harmonization rule | Datasets affected | Practical instruction |
| --- | --- | --- |
| Standardize sex to `male` / `female` | FINDEX, LFS, ELMPS | Recode source-specific binaries into a common categorical field. |
| Standardize settlement to `urban` / `rural` | FINDEX, LFS, ELMPS | Collapse any special codes such as refugee camps if they appear. |
| Collapse education to a common 3- or 4-level scheme | FINDEX, LFS, ELMPS | Suggested common scheme: `low`, `secondary`, `post-secondary`, `university_plus`. |
| Derive `in_workforce` consistently | FINDEX, LFS, ELMPS | Findex uses a direct flag; LFS/ELMPS derive it from labor-force status. |
| Keep both raw and binary credit/payment channel fields where skip logic exists | FINDEX, ELMPS | For example, keep the wage-payment universe and derive separate channel dummies. |
| Reshape ELMPS enterprise blocks to long format | ELMPS raw cross-section | Create one SME row per `enterprise_slot`, dropping empty enterprise slots. |
| Keep linkage keys separate from modeled attributes | ELMPS raw cross-section | Preserve `hhid`, `indid`, `pn`, and `enterprise_manager_person_number` for later joins. |

## Recommended Next Step

After this attribute selection, the next implementation step should be:

1. Create a machine-readable variable map with final harmonized names and recode rules.
2. Build extract-transform scripts for:
   - `persons` from LFS 2024 plus ELMPS/Findex enrichers.
   - `smes` from reshaped ELMPS enterprise blocks.
3. Inspect overlap completeness and missingness before choosing the first Bayesian-network structure.
