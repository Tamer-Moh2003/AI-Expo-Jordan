-- Final Schema for STMS
USE stms_db;
GO

-- Create Tables
CREATE TABLE detectors (
    id VARCHAR(50) PRIMARY KEY,
    location_name VARCHAR(100),
    approach VARCHAR(50)
);

CREATE TABLE counts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    detector_id VARCHAR(50) FOREIGN KEY REFERENCES detectors(id),
    timestamp DATETIME,
    vehicle_count INT
);

CREATE TABLE signal_events (
    id INT IDENTITY(1,1) PRIMARY KEY,
    intersection_id VARCHAR(50),
    phase_number INT,
    light_state VARCHAR(20),
    timestamp DATETIME
);

CREATE TABLE incidents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME,
    event_type VARCHAR(50),
    approach VARCHAR(50),
    confidence DECIMAL(5,2),
    queue_estimate INT,
    snapshot_path VARCHAR(255),
    clip_path VARCHAR(255)
);

CREATE TABLE forecasts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME,
    approach VARCHAR(50),
    predicted_count INT,
    lower_bound INT,
    upper_bound INT
);

CREATE TABLE recommendations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME,
    recommended_phase INT,
    recommended_green_duration INT,
    reason VARCHAR(255),
    estimated_saving_vehicle_minutes DECIMAL(5,2)
);

CREATE TABLE system_health (
    id INT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME,
    ingestion_rate_fps INT,
    dropped_frames INT,
    stream_uptime_seconds INT
);
GO