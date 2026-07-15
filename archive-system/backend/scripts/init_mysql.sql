-- MySQL 初始化脚本
-- 创建数据库（如果不存在）和初始种子数据

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(200),
    contact VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'reviewer',
    is_active BOOLEAN DEFAULT TRUE,
    login_attempts INT DEFAULT 0,
    locked_until DATETIME NULL,
    password_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    permissions JSON,
    data_scope JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS archives (
    id INT AUTO_INCREMENT PRIMARY KEY,
    archive_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    year INT,
    category VARCHAR(100),
    department VARCHAR(200),
    fonds_id VARCHAR(50),
    retention_period VARCHAR(50),
    security_level VARCHAR(50),
    file_count INT DEFAULT 0,
    ocr_text LONGTEXT,
    ocr_status VARCHAR(20) DEFAULT 'pending',
    ocr_confidence DOUBLE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_year (year),
    INDEX idx_category (category),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS review_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    batch_name VARCHAR(100),
    total_count INT DEFAULT 0,
    completed_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    filter_criteria JSON,
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS review_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    archive_id VARCHAR(100),
    risk_score DOUBLE,
    risk_level VARCHAR(10),
    sensitive_items JSON,
    suggestion VARCHAR(50),
    reason TEXT,
    confidence DOUBLE,
    model_name VARCHAR(100),
    processing_time_ms INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task (task_id),
    INDEX idx_archive (archive_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocr_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(200) NOT NULL,
    total_pages INT DEFAULT 0,
    processed_pages INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    filter_criteria JSON,
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(50),
    operation_type VARCHAR(50),
    module VARCHAR(50),
    description TEXT,
    target_id VARCHAR(200),
    ip_address VARCHAR(50),
    result VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_type (operation_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sync_type VARCHAR(20),
    sync_mode VARCHAR(20),
    new_files INT DEFAULT 0,
    updated_files INT DEFAULT 0,
    new_records INT DEFAULT 0,
    updated_records INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    status VARCHAR(20),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME NULL,
    log_detail TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 种子数据：预设角色
INSERT INTO roles (name, description, permissions, data_scope) VALUES
('system_admin', '系统管理员', '{"all": true}', '{"all": true}'),
('archive_admin', '档案管理员', '{"search": true, "ocr": true, "sync": true, "stats": true, "review": false}', '{"all": true}'),
('reviewer', '审核员', '{"search": true, "review": true}', '{"departments": []}')
ON DUPLICATE KEY UPDATE name=name;

-- 种子数据：默认管理员 (密码: Admin@123456)
INSERT INTO users (username, name, role, password_hash)
VALUES ('admin', '系统管理员', 'system_admin', '$2b$12$LJ3m4ys3Lk0TSwHCpNqrNeX9KxMPP6KhZzdM5qK7kKbFkVOZL5R3u')
ON DUPLICATE KEY UPDATE username=username;
