ALTER TABLE prospective.daily_scores
    ADD COLUMN run_id text REFERENCES prospective.forecast_runs(run_id);

CREATE INDEX daily_scores_run_idx
    ON prospective.daily_scores (run_id);
