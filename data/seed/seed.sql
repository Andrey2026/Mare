-- dim_date: January-December 2025
INSERT INTO dim_date VALUES (20250101, '2025-01-01', 2025, 1, 1, 'January');
INSERT INTO dim_date VALUES (20250201, '2025-02-01', 2025, 2, 1, 'February');
INSERT INTO dim_date VALUES (20250301, '2025-03-01', 2025, 3, 1, 'March');
INSERT INTO dim_date VALUES (20250401, '2025-04-01', 2025, 4, 2, 'April');
INSERT INTO dim_date VALUES (20250501, '2025-05-01', 2025, 5, 2, 'May');
INSERT INTO dim_date VALUES (20250601, '2025-06-01', 2025, 6, 2, 'June');
INSERT INTO dim_date VALUES (20250701, '2025-07-01', 2025, 7, 3, 'July');
INSERT INTO dim_date VALUES (20250801, '2025-08-01', 2025, 8, 3, 'August');
INSERT INTO dim_date VALUES (20250901, '2025-09-01', 2025, 9, 3, 'September');
INSERT INTO dim_date VALUES (20251001, '2025-10-01', 2025, 10, 4, 'October');
INSERT INTO dim_date VALUES (20251101, '2025-11-01', 2025, 11, 4, 'November');
INSERT INTO dim_date VALUES (20251201, '2025-12-01', 2025, 12, 4, 'December');

-- dim_manager
INSERT INTO dim_manager VALUES (1, 'Ivanov A.S.', 'Sales');
INSERT INTO dim_manager VALUES (2, 'Petrova M.V.', 'Sales');
INSERT INTO dim_manager VALUES (3, 'Sidorov K.L.', 'Enterprise');

-- dim_contract
INSERT INTO dim_contract VALUES (101, 'Alpha LLC', 'active', 1, '2024-01-15', NULL, 'service');
INSERT INTO dim_contract VALUES (102, 'Beta Corp', 'terminated', 2, '2023-06-01', '2025-03-15', 'license');
INSERT INTO dim_contract VALUES (103, 'Gamma Inc', 'active', 1, '2024-07-01', NULL, 'service');
INSERT INTO dim_contract VALUES (104, 'Delta Ltd', 'terminated', 3, '2022-01-01', '2025-01-31', 'license');
INSERT INTO dim_contract VALUES (105, 'Epsilon SA', 'active', 2, '2025-01-01', NULL, 'service');

-- fact_revenue
INSERT INTO fact_revenue VALUES (1, 101, 20250101, 150000.00, 'monthly');
INSERT INTO fact_revenue VALUES (2, 101, 20250201, 150000.00, 'monthly');
INSERT INTO fact_revenue VALUES (3, 101, 20250301, 150000.00, 'monthly');
INSERT INTO fact_revenue VALUES (4, 102, 20250101, 80000.00, 'monthly');
INSERT INTO fact_revenue VALUES (5, 102, 20250201, 80000.00, 'monthly');
INSERT INTO fact_revenue VALUES (6, 102, 20250301, 40000.00, 'final');
INSERT INTO fact_revenue VALUES (7, 103, 20250101, 200000.00, 'monthly');
INSERT INTO fact_revenue VALUES (8, 103, 20250201, 200000.00, 'monthly');
INSERT INTO fact_revenue VALUES (9, 104, 20250101, 50000.00, 'final');
INSERT INTO fact_revenue VALUES (10, 105, 20250101, 120000.00, 'monthly');
INSERT INTO fact_revenue VALUES (11, 105, 20250201, 120000.00, 'monthly');
INSERT INTO fact_revenue VALUES (12, 105, 20250301, 120000.00, 'monthly');

-- fact_contract_events
INSERT INTO fact_contract_events VALUES (1, 102, 20250301, 'termination', 0);
INSERT INTO fact_contract_events VALUES (2, 104, 20250101, 'termination', 0);
INSERT INTO fact_contract_events VALUES (3, 101, 20250101, 'renewal', 150000.00);
INSERT INTO fact_contract_events VALUES (4, 105, 20250101, 'activation', 120000.00);

-- stg_contract_events (raw staging data)
INSERT INTO stg_contract_events VALUES (1, 102, '2025-03-15', 'termination', 0, 'crm_v2');
INSERT INTO stg_contract_events VALUES (2, 104, '2025-01-31', 'termination', 0, 'crm_v2');
INSERT INTO stg_contract_events VALUES (3, 101, '2025-01-15', 'renewal', 150000.00, 'crm_v2');
INSERT INTO stg_contract_events VALUES (4, 105, '2025-01-01', 'activation', 120000.00, 'billing');
INSERT INTO stg_contract_events VALUES (5, 103, '2025-04-01', 'amendment', 210000.00, 'crm_v2');
INSERT INTO stg_contract_events VALUES (6, 101, '2025-04-01', 'payment', 150000.00, 'billing');
INSERT INTO stg_contract_events VALUES (7, 102, '2025-03-15', 'termination', 0, 'billing');

-- etl_processes
INSERT INTO etl_processes VALUES ('etl_load_stg_contract_events', 'stg_contract_events', 'crm_v2, billing', 'daily 02:00', 'Load raw contract events from source systems');
INSERT INTO etl_processes VALUES ('etl_transform_fact_contract_events', 'fact_contract_events', 'stg_contract_events, dim_contract, dim_date', 'daily 03:00', 'Deduplicate and transform staging events into fact table');
INSERT INTO etl_processes VALUES ('etl_refresh_dm_contract_report', 'dm_contract_report', 'fact_revenue, fact_contract_events, dim_contract, dim_manager, dim_date', 'daily 05:00', 'Rebuild contract reporting mart from fact and dimension tables');

-- etl_execution_log: normal runs + today's slow run for scenario 2
INSERT INTO etl_execution_log VALUES (1, 'etl_refresh_dm_contract_report', '2025-05-08 05:00:00', '2025-05-08 05:15:12', 'success', 5200, 912);
INSERT INTO etl_execution_log VALUES (2, 'etl_refresh_dm_contract_report', '2025-05-09 05:00:00', '2025-05-09 05:14:45', 'success', 5350, 885);
INSERT INTO etl_execution_log VALUES (3, 'etl_refresh_dm_contract_report', '2025-05-10 05:00:00', '2025-05-10 05:16:01', 'success', 5400, 961);
INSERT INTO etl_execution_log VALUES (4, 'etl_refresh_dm_contract_report', '2025-05-11 05:00:00', '2025-05-11 05:32:47', 'success', 18700, 1967);
INSERT INTO etl_execution_log VALUES (5, 'etl_load_stg_contract_events', '2025-05-08 02:00:00', '2025-05-08 02:03:22', 'success', 1200, 202);
INSERT INTO etl_execution_log VALUES (6, 'etl_load_stg_contract_events', '2025-05-09 02:00:00', '2025-05-09 02:03:15', 'success', 1250, 195);
INSERT INTO etl_execution_log VALUES (7, 'etl_load_stg_contract_events', '2025-05-10 02:00:00', '2025-05-10 02:03:40', 'success', 1300, 220);
INSERT INTO etl_execution_log VALUES (8, 'etl_load_stg_contract_events', '2025-05-11 02:00:00', '2025-05-11 02:08:55', 'success', 8500, 535);
INSERT INTO etl_execution_log VALUES (9, 'etl_transform_fact_contract_events', '2025-05-11 03:00:00', '2025-05-11 03:12:30', 'success', 8200, 750);

-- etl_process_logs: today's anomalous run
INSERT INTO etl_process_logs VALUES (1, 'etl_refresh_dm_contract_report', '2025-05-11 05:00:00', 'INFO', 'Starting refresh of dm_contract_report');
INSERT INTO etl_process_logs VALUES (2, 'etl_refresh_dm_contract_report', '2025-05-11 05:00:01', 'INFO', 'Reading from fact_revenue: 12 rows');
INSERT INTO etl_process_logs VALUES (3, 'etl_refresh_dm_contract_report', '2025-05-11 05:00:02', 'INFO', 'Reading from fact_contract_events: 8200 rows');
INSERT INTO etl_process_logs VALUES (4, 'etl_refresh_dm_contract_report', '2025-05-11 05:05:00', 'WARNING', 'Hash join fallback: index on (contract_id, event_date_id) not used due to stale statistics');
INSERT INTO etl_process_logs VALUES (5, 'etl_refresh_dm_contract_report', '2025-05-11 05:15:00', 'WARNING', 'Full table scan on stg_contract_events: 8500 rows (3.5x average)');
INSERT INTO etl_process_logs VALUES (6, 'etl_refresh_dm_contract_report', '2025-05-11 05:32:47', 'INFO', 'Refresh complete: 18700 rows written, duration 1967s (2.1x average)');
