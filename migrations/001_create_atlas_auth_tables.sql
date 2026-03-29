-- AtlasUserAuth baseline migration
-- Creates app access and session tables if they do not already exist.

IF OBJECT_ID('dbo.AtlasAppAccess', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AtlasAppAccess (
        Id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        EmployeeID INT NOT NULL,
        AppKey NVARCHAR(100) NOT NULL,
        Role NVARCHAR(100) NOT NULL CONSTRAINT DF_AtlasAppAccess_Role DEFAULT ('user'),
        RightsJson NVARCHAR(MAX) NOT NULL CONSTRAINT DF_AtlasAppAccess_RightsJson DEFAULT ('{}'),
        IsActive BIT NOT NULL CONSTRAINT DF_AtlasAppAccess_IsActive DEFAULT (1),
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_AtlasAppAccess_CreatedAt DEFAULT (SYSUTCDATETIME()),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_AtlasAppAccess_UpdatedAt DEFAULT (SYSUTCDATETIME())
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UQ_AtlasAppAccess_Employee_App'
      AND object_id = OBJECT_ID('dbo.AtlasAppAccess')
)
BEGIN
    CREATE UNIQUE INDEX UQ_AtlasAppAccess_Employee_App
    ON dbo.AtlasAppAccess(EmployeeID, AppKey);
END;
GO

IF OBJECT_ID('dbo.AtlasSessions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AtlasSessions (
        SessionId NVARCHAR(128) NOT NULL PRIMARY KEY,
        EmployeeID INT NOT NULL,
        CreatedAtEpoch INT NOT NULL,
        LastSeenAtEpoch INT NOT NULL,
        CsrfToken NVARCHAR(128) NOT NULL
    );

    CREATE INDEX IX_AtlasSessions_EmployeeID ON dbo.AtlasSessions(EmployeeID);
END;
GO
