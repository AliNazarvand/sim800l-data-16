# Validation Report

Generated: 2026-10-14T00:20:07Z
Dependencies available: True
## dat_01_at_command: OK (365 records)
## dat_02_urc: OK (95 records)
## dat_03_error_code: 1 errors (1 records)
  - [L1] Record 0: None is not of type 'string'
## dat_04_timing_timeout: OK (5 records)
## dat_05_state_machine: OK (31 records)
## dat_06_init_sequence: 30 errors (35 records)
  - [L1] Record 0: None is not of type 'integer'
  - [L1] Record 1: None is not of type 'integer'
  - [L1] Record 2: None is not of type 'integer'
  - [L1] Record 3: None is not of type 'integer'
  - [L1] Record 4: None is not of type 'integer'
  - [L1] Record 5: None is not of type 'integer'
  - [L1] Record 6: None is not of type 'integer'
  - [L1] Record 7: None is not of type 'integer'
  - [L1] Record 8: None is not of type 'integer'
  - [L1] Record 9: None is not of type 'integer'
  - [L1] Record 10: None is not of type 'integer'
  - [L1] Record 11: None is not of type 'integer'
  - [L1] Record 12: None is not of type 'integer'
  - [L1] Record 13: None is not of type 'integer'
  - [L1] Record 14: None is not of type 'integer'
  - [L1] Record 16: 'dat_06_0001' is not of type 'integer', 'null'
  - [L1] Record 17: 'dat_06_0002' is not of type 'integer', 'null'
  - [L1] Record 18: 'dat_06_0003' is not of type 'integer', 'null'
  - [L1] Record 19: 'dat_06_0004' is not of type 'integer', 'null'
  - [L1] Record 20: 'dat_06_0005' is not of type 'integer', 'null'
## dat_07_hardware_reference: OK (77 records)
## dat_08_firmware_compatibility: 1 errors (1 records)
  - [L1] Record 0: None is not of type 'string'
## dat_09_sms: 14 errors (14 records)
  - [L1] Record 0: None is not of type 'string'
  - [L1] Record 1: None is not of type 'string'
  - [L1] Record 2: None is not of type 'string'
  - [L1] Record 3: None is not of type 'string'
  - [L1] Record 4: None is not of type 'string'
  - [L1] Record 5: None is not of type 'string'
  - [L1] Record 6: None is not of type 'string'
  - [L1] Record 7: None is not of type 'string'
  - [L1] Record 8: None is not of type 'string'
  - [L1] Record 9: None is not of type 'string'
  - [L1] Record 10: None is not of type 'string'
  - [L1] Record 11: None is not of type 'string'
  - [L1] Record 12: None is not of type 'string'
  - [L1] Record 13: None is not of type 'string'
## dat_10_gprs_data: OK (24 records)
## dat_11_http_ftp_ssl: OK (38 records)
## dat_12_audio: 1 errors (13 records)
  - [L1] Record 12: None is not of type 'string'
## dat_13_sim_management: 10 errors (10 records)
  - [L1] Record 0: None is not of type 'string'
  - [L1] Record 1: None is not of type 'string'
  - [L1] Record 2: None is not of type 'string'
  - [L1] Record 3: None is not of type 'string'
  - [L1] Record 4: None is not of type 'string'
  - [L1] Record 5: None is not of type 'string'
  - [L1] Record 6: None is not of type 'string'
  - [L1] Record 7: None is not of type 'string'
  - [L1] Record 8: None is not of type 'string'
  - [L1] Record 9: None is not of type 'string'
## dat_14_operator_apn: OK (52 records)
## dat_15_power_management: 1 errors (1 records)
  - [L1] Record 0: None is not of type 'string'
## dat_16_board_evb: 1 errors (1 records)
  - [L1] Record 0: None is not of type 'string'
## dat_17_certificate_key_store: OK (9 records)
## dat_18_certification: 1 errors (1 records)
  - [L1] Record 0: None is not of type 'string'

## Summary

| Dataset | Records | Errors | Schema |
|---|---|---|---|
| dat_01_at_command | 365 | 0 | yes |
| dat_02_urc | 95 | 0 | yes |
| dat_03_error_code | 1 | 1 | yes |
| dat_04_timing_timeout | 5 | 0 | yes |
| dat_05_state_machine | 31 | 0 | yes |
| dat_06_init_sequence | 35 | 30 | yes |
| dat_07_hardware_reference | 77 | 0 | yes |
| dat_08_firmware_compatibility | 1 | 1 | yes |
| dat_09_sms | 14 | 14 | yes |
| dat_10_gprs_data | 24 | 0 | yes |
| dat_11_http_ftp_ssl | 38 | 0 | yes |
| dat_12_audio | 13 | 1 | yes |
| dat_13_sim_management | 10 | 10 | yes |
| dat_14_operator_apn | 52 | 0 | yes |
| dat_15_power_management | 1 | 1 | yes |
| dat_16_board_evb | 1 | 1 | yes |
| dat_17_certificate_key_store | 9 | 0 | yes |
| dat_18_certification | 1 | 1 | yes |

**Total records: 773**
**Total errors: 60**