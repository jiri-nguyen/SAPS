---
id: ADR-0006
title: "ADR-0006: Store invoice files in SeaweedFS through the S3 API"
status: proposed         # proposed | accepted | rejected | deprecated | superseded
date: 2026-11-28         # date of the latest status change
owner: "Solution Architect (our company)"
deciders: ["Solution Architect (our company)"]
consulted: ["Tech Lead (TBD)"]
last_updated: 2026-11-28
supersedes: ""
superseded_by: ""
related: [CON-01, CON-02, NFR-SCAL-001, ADR-0001, ADR-0003, ADR-0004]
---

# ADR-0006: Store invoice files in SeaweedFS through the S3 API

## Context and Problem Statement
Accounting Members upload invoice files (PDF or image). The SAPS API stores each file; the SAPS Worker reads it for
extraction ([ADR-0004](0004-process-invoices-in-background-worker.md)); users view it during exception handling and
review. The PoC runs locally with Docker Compose ([CON-01](../arc42/02-constraints.md)). After the PoC the system runs
in a cloud that is not chosen yet (MTG-20261114 Q27) and must scale ([NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)).
The Solution Architect first considered MinIO, but its community edition stopped publishing official images in
October 2025, went into maintenance mode on 2025-12-03 and was archived on 2026-02-12 (secondary reports).

**Question:** Where are invoice files stored, and through which interface?

## Decision Drivers
- Shared by several containers (SAPS API, SAPS Worker) and several instances — [NFR-SCAL-001](../../01-requirements/nfr.md#nfr-scal-001)
- Runs locally with Docker Compose — [CON-01](../arc42/02-constraints.md)
- Easy move to cloud object storage later (Amazon S3; Azure Blob through an adapter)
- Actively maintained, open-source license
- Preference of the Solution Architect (2026-11-28) for object storage

## Considered Options
1. Docker volume (local file system) shared by the containers
2. PostgreSQL (`bytea` / large objects)
3. MinIO (last official community image)
4. SeaweedFS with its S3 API
5. Garage with its S3 API

## Decision Outcome
**Chosen option:** "SeaweedFS with its S3 API", chosen by the Solution Architect, because it gives object storage
with an S3-compatible API in a single local container, is actively maintained under the Apache-2.0 license, and lets
the code use the standard S3 API that Amazon S3 offers natively.

- New container: **SAPS File Storage** (SeaweedFS, upstream image `chrislusf/seaweedfs`, `weed server -s3`).
- Code accesses files only through a **File Storage Port** (put, get, delete, optional presigned URL), implemented
  with an S3 client library. Amazon S3 can replace SeaweedFS by configuration; Azure Blob needs its own adapter
  (same pattern as [ADR-0001](0001-isolate-extraction-and-erp-behind-ports.md)).
- Object key: `invoices/{invoice_id}/{file_sha256}`; the key is stored in `Invoice.file_storage_key`
  ([data model](../data-model.md#invoice)).
- Write order on upload: store the object first, then commit the invoice row. A failed commit can leave an orphan
  object; orphans are harmless in the PoC and can be cleaned up later.

### Consequences
- **Good:** Files are shared by all containers and instances; no shared file system needed.
- **Good:** The S3 API is the most common object storage interface; moving to Amazon S3 is a configuration change.
- **Good:** The database stays small; files do not bloat backups or queries.
- **Bad:** One more container (Docker Compose now runs six: SAPS Web App, SAPS API, SAPS Worker, SAPS Message Broker,
  SAPS File Storage, SAPS Database).
- **Bad:** SeaweedFS is less familiar to the team than MinIO; its S3 compatibility for our operations must be checked.
- **Neutral:** Azure Blob is not S3-compatible; an Azure deployment needs a second adapter behind the File Storage Port.

### Confirmation
- Spike (same Linear spike as ADR-0004): put, get and delete through the S3 client library against SeaweedFS in
  Docker Compose; presigned GET URL works from the browser; data survives a container restart (volume mounted).
- Integration tests run against SeaweedFS with Testcontainers.
- ADR status moves to `accepted` after the spike; if the spike fails, a new ADR records the alternative.

## Pros and Cons of the Options

### Docker volume
- Good, because it is the simplest; no new container.
- Bad, because a shared file system does not exist in most cloud container services, so the storage code changes later.

### PostgreSQL
- Good, because file and invoice are written in one transaction.
- Bad, because large binary data bloats the database and its backups, and does not scale well.

### MinIO (last official community image)
- Good, because it is the best-known self-hosted S3 server.
- Bad, because the community edition is archived: no new images and no committed security fixes.

### SeaweedFS
- Good, because it is actively maintained (release 4.39 on 2026-07-10 per a third-party tracker) and Apache-2.0 licensed.
- Good, because it runs as one container with an S3 API.
- Bad, because S3 compatibility is partial in places and must be checked for the operations we use.

### Garage
- Good, because it is lightweight and simple to run.
- Bad, because it is AGPL-3.0 licensed and implements a smaller part of the S3 API.

## More Information
- Customer agreement: not required (internal design decision); mentioned to the Product Owner together with Redis
  ([ADR-0004](0004-process-invoices-in-background-worker.md)) as an addition to the stack agreed in
  [DEC-019](../../01-requirements/decision-log.md#dec-019).
- References: [SeaweedFS Getting Started](https://github.com/chrislusf/seaweedfs/wiki/Getting-Started),
  [MinIO CE status (secondary source)](https://glukhov.org/data-infrastructure/object-storage/minio-dead/).
