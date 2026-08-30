ALTER TABLE prospective.forecast_runs
    ADD COLUMN state_id char(64) REFERENCES prospective.model_states(state_id);

CREATE INDEX forecast_runs_state_idx
    ON prospective.forecast_runs (state_id);
