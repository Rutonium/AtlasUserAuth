-- AtlasUserAuth migration 003
-- Creates app rights definition matrix storage.

IF OBJECT_ID('dbo.AtlasAppRightDefinitions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AtlasAppRightDefinitions (
        Id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        AppKey NVARCHAR(100) NOT NULL,
        RightKey NVARCHAR(120) NOT NULL,
        Level1 BIT NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_Level1 DEFAULT (0),
        Level2 BIT NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_Level2 DEFAULT (0),
        Level3 BIT NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_Level3 DEFAULT (0),
        Level4 BIT NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_Level4 DEFAULT (0),
        Level5 BIT NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_Level5 DEFAULT (0),
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_CreatedAt DEFAULT (SYSUTCDATETIME()),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_AtlasAppRightDefinitions_UpdatedAt DEFAULT (SYSUTCDATETIME())
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UQ_AtlasAppRightDefinitions_App_Right'
      AND object_id = OBJECT_ID('dbo.AtlasAppRightDefinitions')
)
BEGIN
    CREATE UNIQUE INDEX UQ_AtlasAppRightDefinitions_App_Right
    ON dbo.AtlasAppRightDefinitions(AppKey, RightKey);
END;
GO
