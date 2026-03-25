# Synthetic Population Egypt

This repository contains the code and exported artifacts used to generate and validate the Egypt synthetic population used in this project.

It is intentionally limited to:

- the synthetic population generation model
- the validation workflow
- the synthetic population documentation and reports
- the learned model artifacts used by the generator
- the resulting synthetic person and SME populations
- the validation plots and summary tables

It does not include the raw source datasets. The repository only contains an empty `data/` folder as a placeholder.

## Repository Structure

- `model.py`: main pipeline for harmonizing source inputs, learning the probabilistic structure, and generating synthetic persons and SMEs
- `validation.py`: validation workflow comparing synthetic outputs against the original harmonized sources
- `docs/`: schema documentation, variable-selection notes, and validation report
- `outputs/`: learned model artifacts, generated synthetic populations, and validation outputs
- `data/`: empty placeholder folder for raw inputs, intentionally not versioned here

## Included Outputs

The repository includes the following generated populations:

- `outputs/egypt_synthetic_persons_1000.csv`
- `outputs/egypt_synthetic_persons_10000.csv`
- `outputs/egypt_synthetic_persons_20000.csv`
- `outputs/egypt_synthetic_smes_1000.csv`
- `outputs/egypt_synthetic_smes_10000.csv`
- `outputs/egypt_synthetic_smes_20000.csv`

It also includes:

- learned Bayesian-network artifacts in `outputs/`
- validation figures and metrics in `outputs/validation/`
- the synthetic population schema in `docs/egypt_synthetic_population_schema.md`
- the validation report in `docs/egypt_synthetic_population_validation.md`

## Data Requirements

The generation code expects the raw source files to be placed manually in the `data/` directory using the same subfolder layout referenced in `model.py`. Those files are not distributed in this repository.

Expected source groups:

- `data/LFS 2024/`
- `data/FINDEX 2024/`
- `data/ELMPS 2023/`

## How To Run

Create synthetic populations:

```powershell
python model.py --sample-sizes 1000 10000 20000
```

Run validation:

```powershell
python validation.py --sample-sizes 1000 10000
```

## Notes

- The code in this repository is the synthetic-population generation layer only. It does not include the downstream simulation repository.
- The exported outputs are kept so the repository is reproducible as a data product even without redistributing the raw microdata.
