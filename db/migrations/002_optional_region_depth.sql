ALTER TABLE prospective.regions
    ALTER COLUMN minimum_depth_km DROP NOT NULL,
    ALTER COLUMN minimum_depth_km DROP DEFAULT;
