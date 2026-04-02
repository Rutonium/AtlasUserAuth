-- AtlasUserAuth migration 002
-- Adds normalized access level metadata to AtlasAppAccess.

IF COL_LENGTH('dbo.AtlasAppAccess', 'AccessLevel') IS NULL
BEGIN
    ALTER TABLE dbo.AtlasAppAccess
    ADD AccessLevel INT NOT NULL CONSTRAINT DF_AtlasAppAccess_AccessLevel DEFAULT (1);
END;
GO

IF COL_LENGTH('dbo.AtlasAppAccess', 'AccessLabel') IS NULL
BEGIN
    ALTER TABLE dbo.AtlasAppAccess
    ADD AccessLabel NVARCHAR(100) NULL;
END;
GO

UPDATE dbo.AtlasAppAccess
SET AccessLabel =
    CASE ISNULL(AccessLevel, 1)
        WHEN 1 THEN 'Viewer'
        WHEN 2 THEN 'Contributor'
        WHEN 3 THEN 'Specialist'
        WHEN 4 THEN 'Manager'
        WHEN 5 THEN 'Owner'
        ELSE 'Custom'
    END
WHERE AccessLabel IS NULL OR LTRIM(RTRIM(AccessLabel)) = '';
GO
