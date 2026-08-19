# Data Provenance

The source `earthquake.db` is an input snapshot, never a committed project
artifact. Its current contract is recorded in the reference manifest.

The database contains 5,086,795 earthquake rows over 1901-11-14 through
2026-08-19 and is approximately 1.5 GB. Copying it wholesale would also copy
application-specific tables and heterogeneous catalog history that are not
part of the ETAS experiment.

The local export will therefore create a new database containing only the
region, time, magnitude, status, and provenance fields required by the locked
experiment. The export is not allowed to alter the source database.

Every export report must include source and destination checksums, SQL or tool
version, row counts, exclusions, and observed bounds.

