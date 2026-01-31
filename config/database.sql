-- config/database.sql
DROP TABLE IF EXISTS conversation_context CASCADE;
DROP TABLE IF EXISTS appliances CASCADE;
DROP TABLE IF EXISTS survey_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS families CASCADE;
DROP TABLE IF EXISTS appliance_defaults CASCADE;

CREATE TABLE families (
    family_id VARCHAR(50) PRIMARY KEY,
    household_size INT,
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    family_id VARCHAR(50) REFERENCES families(family_id),
    age_group VARCHAR(20),
    interests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE survey_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    family_id VARCHAR(50) REFERENCES families(family_id),
    status VARCHAR(20) DEFAULT 'in_progress',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appliances (
    appliance_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES survey_sessions(session_id),
    user_id VARCHAR(50) REFERENCES users(user_id),
    family_id VARCHAR(50) REFERENCES families(family_id),
    name VARCHAR(100) NOT NULL,
    number INT DEFAULT 1,
    power INT NOT NULL,
    func_time INT NOT NULL,
    num_windows INT DEFAULT 1,
    window_1_start INT,
    window_1_end INT,
    window_2_start INT,
    window_2_end INT,
    window_3_start INT,
    window_3_end INT,
    func_cycle INT DEFAULT 1,
    fixed VARCHAR(3) DEFAULT 'no',
    occasional_use DECIMAL(3,2) DEFAULT 1.0,
    wd_we_type INT DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversation_context (
    context_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES survey_sessions(session_id),
    user_id VARCHAR(50) REFERENCES users(user_id),
    message_order INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    extracted_data TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appliance_defaults (
    appliance_type VARCHAR(100) PRIMARY KEY,
    typical_power_watts INT NOT NULL,
    category VARCHAR(50)
);

INSERT INTO appliance_defaults VALUES
('TV', 100, 'entertainment'),
('Refrigerator', 150, 'kitchen'),
('Washing Machine', 500, 'laundry'),
('Air Conditioner', 1500, 'cooling'),
('Fan', 75, 'cooling'),
('Laptop', 50, 'electronics'),
('Desktop Computer', 200, 'electronics'),
('Microwave', 1000, 'kitchen'),
('LED Light', 10, 'lighting');
