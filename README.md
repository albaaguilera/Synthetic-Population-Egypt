# Synthetic Population Egypt

This repository contains the code used to generate and validate a financial-focused synthetic population for Egypt. In particular:

- the population synthesis bayesian model
- the validation workflow, plots and reports
- the resulting synthetic person and SME populations with documentation reports

It does not include the raw source datasets. The repository only contains an empty `data/` folder as a placeholder.

## Repository Structure

- `model.py`: main pipeline for harmonizing source inputs, learning the probabilistic structure, and generating synthetic persons and SMEs
- `validation.py`: validation workflow comparing synthetic outputs against the original harmonized sources
- `docs/`: schema documentation, variable-selection notes, and validation report
- `outputs/`: learned model artifacts, generated synthetic populations, and validation outputs
- `data/`: empty placeholder folder for raw inputs, intentionally not versioned here

## Included Outputs

The repository includes: 

- `outputs/egypt_synthetic_persons_N.csv`: the generated populations for number of agents N = 1000, 10000, 20000:
- learned Bayesian-network in `outputs/`
- validation figures and metrics in `outputs/validation/`
- the synthetic population documentation in `docs/egypt_synthetic_population_schema.md`
- the validation report in `docs/egypt_synthetic_population_validation.md`

## How To Run

Create synthetic populations:

```powershell
python model.py --sample-sizes 1000 10000 20000
```

Run validation:

```powershell
python validation.py --sample-sizes 1000 10000
```


## Data Requirements

The generation code expects the raw source files to be placed manually in the `data/` directory using the same subfolder layout referenced in `model.py`. Those files are not distributed in this repository.

Expected source groups:

- `data/LFS 2024/` - Economic Research Forum
- `data/FINDEX 2024/` - World Bank
- `data/ELMPS 2023/` - Economic Research Forum


