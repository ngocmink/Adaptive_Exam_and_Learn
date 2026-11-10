-- Runs only when the PostgreSQL volume is first initialized.
-- psql executes this connected as POSTGRES_USER, who owns the new database.
CREATE DATABASE exam_test;
