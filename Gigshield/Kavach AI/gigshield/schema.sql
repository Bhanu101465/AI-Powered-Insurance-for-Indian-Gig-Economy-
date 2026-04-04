-- Run this in phpMyAdmin or MySQL Workbench
-- First create the database
CREATE DATABASE IF NOT EXISTS gigshield;
USE gigshield;

-- Workers table
CREATE TABLE workers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    city VARCHAR(50),
    zone ENUM('low', 'medium', 'high') DEFAULT 'low',
    platform ENUM('amazon_flex', 'flipkart_ekart', 'other') DEFAULT 'other',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policies table
CREATE TABLE policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_id INT NOT NULL,
    plan VARCHAR(50),
    weekly_premium DECIMAL(10,2),
    coverage_amount DECIMAL(10,2),
    start_date DATE,
    end_date DATE,
    status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

-- Claims table
CREATE TABLE claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_id INT NOT NULL,
    policy_id INT,
    reason TEXT,
    status ENUM('triggered', 'processing', 'paid', 'rejected') DEFAULT 'triggered',
    amount DECIMAL(10,2),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (policy_id) REFERENCES policies(id)
);
