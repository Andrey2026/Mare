-- Staging
CREATE TABLE IF NOT EXISTS stg_contract_events (
    event_id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2),
    source_system VARCHAR(50)
);

-- Dimension
CREATE TABLE IF NOT EXISTS dim_contract (
    contract_id INTEGER PRIMARY KEY,
    client_name VARCHAR(100) NOT NULL,
    contract_status VARCHAR(20) NOT NULL,
    manager_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    contract_type VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_manager (
    manager_id INTEGER PRIMARY KEY,
    manager_name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month_name VARCHAR(10) NOT NULL
);

-- Fact
CREATE TABLE IF NOT EXISTS fact_revenue (
    revenue_id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES dim_contract(contract_id),
    date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    amount DECIMAL(15,2) NOT NULL,
    revenue_type VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_contract_events (
    event_id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES dim_contract(contract_id),
    event_date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
    event_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2)
);

-- ETL Metadata
CREATE TABLE IF NOT EXISTS etl_processes (
    process_name VARCHAR(100) PRIMARY KEY,
    target_table VARCHAR(100) NOT NULL,
    source_tables VARCHAR(500) NOT NULL,
    schedule VARCHAR(50) NOT NULL,
    description VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS etl_execution_log (
    execution_id INTEGER PRIMARY KEY,
    process_name VARCHAR(100) NOT NULL REFERENCES etl_processes(process_name),
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    rows_affected INTEGER,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS etl_process_logs (
    log_id INTEGER PRIMARY KEY,
    process_name VARCHAR(100) NOT NULL REFERENCES etl_processes(process_name),
    timestamp TIMESTAMP NOT NULL,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL
);
