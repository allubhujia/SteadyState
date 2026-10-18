# Data

Nothing in this folder except this file is committed. Pitt and MESA data use agreements forbid redistribution,
so every team member downloads their own copy.

```
data/
├── raw/          files exactly as downloaded, never edited
│   ├── nhanes/   2011-2012/ (_G), 2013-2014/ (_H), each with docs/
│   ├── hrs/      rand_longitudinal/, cognition_imputed/
│   ├── pitt/     transcripts/, audio/, adress/
│   └── mesa/     datasets/, actigraphy/, polysomnography/
├── interim/      cleaned / joined intermediates
└── processed/    final model inputs
```

| Dataset | Source | Access | How to get it |
|---|---|---|---|
| NHANES 2011–2014 | https://wwwn.cdc.gov/nchs/nhanes/ | Public | Manual download, see steps below |
| HRS | https://hrsdata.isr.umich.edu/ | Free account | RAND HRS Longitudinal File (Stata) + imputed cognition file, manual download |
| DementiaBank Pitt | https://dementia.talkbank.org/ | Membership | Manual download after approval |
| MESA Sleep | https://sleepdata.org/datasets/mesa | NSRR request | `nsrr download mesa/datasets` etc. after approval |

## Downloading NHANES

1. Go to https://wwwn.cdc.gov/nchs/nhanes/ and open the **2011–2012** cycle, then repeat for **2013–2014**.
2. Download these files (`_G` = 2011–2012, `_H` = 2013–2014) by clicking the **Data File** link (`.xpt`):

   | Component page | Files |
   |---|---|
   | Demographics | `DEMO_G`, `DEMO_H` |
   | Questionnaire → Cognitive Functioning | `CFQ_G`, `CFQ_H` |
   | Questionnaire → Sleep Disorders | `SLQ_G`, `SLQ_H` |
   | Examination → Physical Activity Monitor (Header, Day, Hour) | `PAXHD_*`, `PAXDAY_*`, `PAXHR_*` |

3. Also save each file's **Doc File** page (`.htm`) and the `PAXMIN_*` doc page.
4. Put the `.xpt` files in `raw/nhanes/2011-2012/` or `raw/nhanes/2013-2014/`, and the `.htm` pages in that cycle's `docs/` subfolder.
5. Optional: minute-level `PAXMIN_G` / `PAXMIN_H` (~17.5 GB together), linked from the same Physical Activity Monitor page. Check free disk space first.

Files are joined on `SEQN`; read with `pd.read_sas(path)`.

Cite each dataset in the format its provider specifies.
