# Egypt Synthetic Population Schema

## Scope

This synthetic population contains two linked entity tables:

- `persons`: synthetic individuals sampled from the learned LFS-FINDEX-ELMPS person network.
- `smes`: synthetic household non-farm enterprises sampled from the learned ELMPS enterprise network and linked to synthetic managers in `persons`.

The requested sample sizes refer to the number of synthetic persons. The number of SMEs is endogenous and is generated from the sampled person-level variable `elmps_num_enterprises_managed`.

## Output Runs

| Persons requested | Synthetic persons | Synthetic SMEs |
| --- | --- | --- |
| 20000 | 20000 | 4318 |

## Persons Table

| Column | Description |
| --- | --- |
| `synthetic_person_id` | Stable synthetic individual identifier. |
| `education_level` | Collapsed education level: low, secondary, post-secondary, or university+. |
| `findex_inc_q` | Within-economy household income quintile. |
| `findex_fin20` | Applied for a loan using a mobile phone (past 12 months). |
| `findex_fin21` | Received this mobile-phone-based loan (conditional on fin20 = Yes). |
| `findex_fin22a` | Borrowed from a bank or similar financial institution. |
| `findex_fin22b` | Borrowed from family or friends. |
| `findex_fin22c` | Borrowed from an informal savings club. |
| `findex_fin22g` | Used a credit card in the past 12 months. |
| `findex_fin22h` | Paid off all credit card balances in full by the due date. |
| `findex_fin23` | Borrowed money from any source for any reason (past 12 months). |
| `findex_fin34d` | Employer paid wages to a card. |
| `findex_fin36a` | Who withdraws wage money from the account (self vs friend/family). |
| `findex_fin31c` | Paid utilities by handing cash to a bank agent/staff. |
| `findex_fh2` | Received money from relatives/friends in a different city (inside country). |
| `findex_fh2a` | Received money from relatives/friends living in a different country in the past 12 months. |
| `findex_fin39c` | Government money received in cash. |
| `findex_fin7` | In the past 12 months, any money put into or taken out of personal accounts (yes/no). |
| `urban_rural` | Settlement type, coded as 0 = urban and 1 = rural. |
| `findex_fin17a` | Saved at a bank or similar financial institution (past 12 months). |
| `findex_fin17b` | Saved at another type of financial institution. |
| `findex_fin22a_1` | Borrowed from a mobile money provider. |
| `findex_fin22d` | Borrowed for health/medical purposes. |
| `findex_fin22f` | Purchased food on credit. |
| `findex_merchantpay_dig` | Made a digital merchant payment in the past 12 months. |
| `elmps_bank_savings_amount_band` | Quantile band of the amount saved in bank accounts. |
| `age_band` | Age band of the individual: 15-24, 25-34, 35-44, 45-54, 55-64, or 65+. |
| `findex_fin39d` | Government money received on a card. |
| `in_workforce` | Labor-force participation, coded as 1 = in workforce and 0 = out of workforce. |
| `findex_account_fin` | Has an account at a financial institution (bank, microfinance, cooperative, etc.). |
| `findex_account` | Has any kind of account (financial institution and/or mobile money). |
| `findex_fin2` | Has a debit/ATM card connected to an account. |
| `findex_fin10` | Has a credit card (can borrow and pay later). |
| `findex_fin11_0` | Has a prepaid / stored-value card that can be loaded and used to send/receive money or pay at multiple places. |
| `findex_fin11_1` | Ever had an account (past experience with formal finance). |
| `findex_fin11_2` | Thinks they could use an account on their own (capability / confidence). |
| `findex_borrowed` | Borrowed from any source in the past 12 months. |
| `findex_pay_utilities` | Paid a utility bill (electricity, water, trash) in the past 12 months. |
| `findex_fin30` | Made regular utility payments (yes/no). |
| `findex_fin31a` | Paid utilities using a bank account. |
| `findex_fin31b` | Paid utilities using a mobile phone. |
| `findex_fin31d` | Pays utilities exclusively in cash. |
| `findex_receive_pensions` | Received government pension. |
| `findex_fin38` | Received a public-sector pension. |
| `findex_fin39a` | Government money received into a bank account. |
| `findex_fin5` | In a typical month, how often money is deposited into personal account(s) (weekly / monthly / < once a month / never). |
| `findex_fin6` | In a typical month, how often money is sent from or taken out of personal account(s). |
| `findex_fin8` | Typically keeps any money in personal account(s) (yes/no). |
| `findex_fin3` | In past 12 months, used card or mobile phone to make payments, buy things, or send/receive money using the account. |
| `findex_fin9a` | In past 12 months, received account-balance information via email / SMS / text about account balance. |
| `findex_fin9b` | In past 12 months, checked account balance using a mobile phone or computer. |
| `findex_fin11a` | Financial institutions are too far away. |
| `findex_fin11b` | Financial service fees are too expensive. |
| `findex_fin11c` | Does not have the necessary documentation. |
| `findex_fin11d` | Does not have enough money to open an account. |
| `findex_fin11e` | A family member already has an account. |
| `findex_fin11f` | Does not trust financial institutions. |
| `elmps_formal_loan_outcome` | Outcome of the formal loan application: approved, rejected, pending, or unknown. |
| `elmps_formal_loan_cost_type` | Type of cost attached to the formal loan, such as interest, fees, both, or none. |
| `elmps_borrowed_from_individuals_last12m` | Whether the individual borrowed informally from other people in the past 12 months. |
| `elmps_amount_borrowed_from_individuals_band` | Quantile band of the amount borrowed from individuals. |
| `elmps_informal_loan_cost_type` | Type of cost attached to the informal loan. |
| `sex` | Sex of the individual, coded as 0 = male and 1 = female. |
| `lfs_region` | Governorate / region code from the LFS sample. |
| `lfs_sector` | Institutional sector of employment: government, public, private, joint/cooperative, foreign, or other. |
| `lfs_job_stability` | Job stability category such as regular, temporary, part-time, or seasonal. |
| `lfs_contract_type` | Type of employment contract, including official, written, verbal, or none. |
| `lfs_health_insurance` | Whether the job provides health insurance coverage. |
| `lfs_social_security` | Whether the job provides social security coverage. |
| `lfs_works_in_establishment` | Whether the individual works in an establishment rather than in dispersed or informal settings. |
| `lfs_establishment_size_band` | Establishment size band from the LFS enterprise-size variable. |
| `lfs_monthly_wage_band` | Quantile band of monthly wage from the main job. |
| `lfs_employer_income_band` | Quantile band of monthly employer income. |
| `findex_dig_account` | Has a digitally enabled account (can be used for digital payments). |
| `findex_saved` | Saved any money in the past 12 months (in an account, mobile money, or informal mechanisms). |
| `findex_fin18` | Received interest on savings in the past 12 months. |
| `findex_fin22e` | Borrowed to start/operate a business. |
| `findex_fin35` | Ever paid an unexpected fee when withdrawing wages from an account. |
| `findex_fin36` | When wages go into an account, usually withdraw all as cash vs leave some in the account. |
| `findex_fh1` | Gave or sent money to relatives/friends in a different city (inside country). |
| `findex_fin28` | Gave or sent domestic remittances directly from an account or phone. |
| `findex_receive_transfers` | Received government transfer. |
| `findex_receive_agriculture` | Received payment for sale of agricultural goods. |
| `findex_fin37` | Received any financial support from the government (e.g. subsidies, education/medical support). |
| `findex_fin39b` | Government money received through a mobile phone. |
| `findex_anydigpayment` | Made or received any digital payment in the past 12 months. |
| `findex_fin26b` | Used a mobile phone or computer to buy something online that was delivered. |
| `findex_fin27` | When buying online, usually pays online vs pays cash on delivery. |
| `elmps_job_formality` | Formality of the main job, coded from the ELMPS formal / informal indicator. |
| `elmps_social_insurance_job` | Whether the main job provides social insurance. |
| `elmps_has_job_contract` | Whether the individual has a job contract in the main job. |
| `elmps_medical_insurance_job` | Whether the main job provides medical insurance. |
| `elmps_paid_leave_job` | Whether the main job includes paid leave. |
| `elmps_paid_sick_leave_job` | Whether the main job includes paid sick leave. |
| `elmps_applied_formal_loan_last12m` | Whether the individual applied for a formal loan in the past 12 months. |
| `elmps_formal_lender_type` | Type of formal lender approached for the loan. |
| `elmps_formal_loan_purpose` | Purpose of the formal loan, including enterprise, consumption, housing, health, education, or debt needs. |
| `elmps_has_bank_account` | Whether the individual has a bank account. |
| `elmps_num_enterprises_managed` | Number of SMEs managed by the individual in the synthetic population. |
| `elmps_manages_sme` | Whether the individual manages at least one SME. |
| `lfs_marital_status` | Marital status category from LFS. |
| `lfs_employment_status` | Employment status in LFS: employee, employer, self-employed, unpaid family worker, or similar. |
| `lfs_occupation_group` | Main-job occupation group from LFS. |
| `lfs_industry_group` | Main-job industry group from LFS. |
| `lfs_workplace_type` | Type of workplace such as home, separate premises, street, transport, construction site, or agricultural land. |
| `lfs_has_secondary_job` | Whether the individual has a secondary job. |
| `lfs_weekly_hours_band` | Quantile band of usual weekly hours worked in the main job. |
| `lfs_self_employed_income_band` | Quantile band of monthly self-employment income. |
| `findex_account_mob` | Has a mobile money account. |
| `findex_fin17c` | Saved using a mobile money account. |
| `findex_fin17e` | Saved using an informal savings club. |
| `findex_fin17f` | Saved in some other way, such as through a person outside the household. |
| `findex_fin19` | Made regular payments to an insurance agent or company in the past 12 months. |
| `findex_receive_wages` | Received wage/salary payment (any channel). |
| `findex_fin32` | Received any salary or wages from an employer in the past 12 months. |
| `findex_fin33` | Employed by the government, military or public sector (past 12 months). |
| `findex_fin34a` | Employer paid wages directly into an account at a bank or similar FI. |
| `findex_fin34b` | Employer paid wages through a mobile phone. |
| `findex_fin34c` | Employer paid wages in cash. |
| `findex_domestic_remittances` | Made or received domestic remittance (coded by account vs non-account). |
| `findex_fin29` | Received domestic remittances directly into an account or phone. |
| `findex_fin26a` | Used a mobile phone or computer to make a bill payment in the past 12 months. |
| `elmps_employment_status` | Employment status in ELMPS: wage employee, employer, self-employed, or unpaid family worker. |
| `elmps_firm_size_band` | Firm-size band of the main job in ELMPS. |
| `elmps_has_secondary_job` | Whether the individual has a second job in ELMPS. |
| `elmps_owns_mobile_phone` | Whether the individual owns a mobile phone. |
| `elmps_has_mobile_wallet` | Whether the individual has a mobile wallet or mobile-money account. |
| `elmps_has_any_savings` | Whether the individual has any savings. |
| `elmps_savings_method` | Main savings channel used by the individual. |
| `elmps_savings_interest_bearing` | Whether the person's savings are interest-bearing. |

## SMEs Table

| Column | Description |
| --- | --- |
| `synthetic_sme_id` | Stable synthetic SME identifier. |
| `synthetic_manager_id` | Identifier of the linked synthetic person managing the SME. |
| `manager_enterprise_sequence` | Sequence number of the SME within the manager's set of enterprises. |
| `manager_sex` | Sex of the SME manager, coded as 0 = male and 1 = female. |
| `manager_age_band` | Age band of the SME manager: 15-24, 25-34, 35-44, 45-54, 55-64, or 65+. |
| `manager_education_level` | Collapsed education level of the SME manager: low, secondary, post-secondary, or university+. |
| `manager_urban_rural` | Settlement type of the SME manager, coded as 0 = urban and 1 = rural. |
| `manager_in_workforce` | Labor-force participation status of the SME manager, coded as 1 = in workforce and 0 = out of workforce. |
| `sme_enterprise_activity_1digit` | Main enterprise activity code at the 1-digit level. |
| `sme_enterprise_age_band` | Enterprise age band derived from the year the business was established. |
| `sme_ownership_structure` | Ownership structure of the enterprise, such as household-only or with outside partners. |
| `sme_household_ownership_share_band` | Quantile band of the household ownership share in the enterprise. |
| `sme_workplace_type` | Type of workplace used by the enterprise, such as home, shop, workshop, kiosk, taxi, field, or online. |
| `sme_current_capital_band` | Current capital band of the enterprise. |
| `sme_startup_capital_band` | Startup capital band of the enterprise when it began. |
| `sme_startup_capital_source` | Main source of startup capital for the enterprise. |
| `sme_primary_buyer_type` | Main buyer category for the enterprise's goods or services. |
| `sme_has_business_license` | Whether the enterprise has a business license. |
| `sme_has_commercial_registration` | Whether the enterprise has commercial registration. |
| `sme_keeps_accounting_books` | Whether the enterprise keeps regular accounting books. |
| `sme_has_online_page_or_storefront` | Whether the enterprise has an online page, social-media page, or electronic storefront. |
| `sme_has_mobile_sales_app` | Whether the enterprise uses a mobile app to display or sell products or services. |
| `sme_share_of_sales_online_band` | Quantile band of the share of sales made through online channels. |
| `sme_hires_nonhousehold_workers` | Whether the enterprise hires workers from outside the household. |
| `sme_num_nonhousehold_workers_band` | Quantile band of the number of non-household workers hired by the enterprise. |
| `sme_num_related_external_workers_band` | Quantile band of the number of hired workers who are relatives. |
| `sme_any_workers_with_social_insurance` | Whether any enterprise workers are covered by social insurance. |
| `sme_num_workers_with_social_insurance_band` | Quantile band of the number of workers with social insurance. |
| `sme_new_workers_joined_last12m` | Whether new workers joined the enterprise during the last 12 months. |
| `sme_workers_left_last12m` | Whether any workers left the enterprise during the last 12 months. |
| `sme_annual_wage_bill_band` | Quantile band of annual spending on workers' wages. |
| `sme_annual_taxes_paid_band` | Quantile band of annual taxes paid by the enterprise. |
| `sme_average_monthly_net_earnings_band` | Quantile band of the enterprise's average monthly net earnings. |

## Coding Notes

- All modeled fields are discrete integer-coded variables.
- `0` is used as a substantive category for some count and money bands where zero is meaningful.
- `-1` denotes missing or structurally unavailable values after harmonization.
