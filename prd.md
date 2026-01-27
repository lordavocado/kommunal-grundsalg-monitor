Kommunal Grundsalg Monitoring
Project Purpose & Rationale
Overview

The purpose of the Kommunal Grundsalg Monitoring project is to automate the discovery and analysis of municipal announcements related to land and property sales (“grundsalg”) across Danish municipality websites.

Today, this information is scattered across heterogeneous public websites and is monitored manually with significant delay and effort. This project aims to replace periodic manual checks with a scalable, near-real-time monitoring system that identifies relevant signals, structures the information, and makes it available for further analysis and product development at Resights.

Problem Statement

Municipalities regularly publish information about land and property sales, tenders, and public offerings. However:

Information is distributed across ~50+ municipality websites with different structures, formats, and publishing practices.

Researchers manually monitor these sites every 3–4 weeks.

The process requires approximately 10 hours per month of manual work.

Relevant announcements are often discovered with a delay of up to 3–4 weeks.

Manual monitoring is repetitive, error-prone, and not scalable.

As a result, Resights risks missing timely signals and cannot fully leverage municipal data as a competitive real estate intelligence source.

Objective

The project aims to design and validate an automated monitoring pipeline that:

Checks municipal websites daily for new or updated content related to grundsalg.

Detects relevant announcements using crawling and keyword-based discovery.

Applies LLM-based analysis to extract structured information (e.g., location, sale type, deadlines, summaries).

Logs findings in a structured data store (initially Google Sheets) and triggers notifications.

Reduces manual monitoring effort while improving timeliness and coverage.

The primary goal is not immediate production deployment, but to validate feasibility, signal quality, and operational complexity.

Strategic Value for Resights

If successful, the project will:

Significantly reduce manual research effort.

Enable near-real-time detection of municipal real estate signals.

Provide structured data that can be integrated into Resights’ data platform.

Serve as a blueprint for monitoring other public-sector signals (planning, zoning, tenders, infrastructure).

Strengthen Resights’ position as a data-driven real estate intelligence platform.

This project also acts as an internal experiment in combining web crawling and large language models for scalable public data extraction.

Scope (Prototype Phase)

In scope:

Monitoring ~50 municipality websites.

Daily automated crawling and discovery.

Keyword-based filtering of relevant content.

LLM-based structured extraction.

Logging results and basic alerting.

Lightweight infrastructure (GitHub Actions + Google Sheets).

Out of scope (initially):

Full production-grade infrastructure.

Customer-facing features.

Perfect recall or complete coverage.

Advanced UI or dashboards.

Success Criteria

The prototype will be considered successful if:

Relevant grundsalg announcements are detected within 24 hours of publication.

Manual monitoring time is reduced by at least 80%.

Extracted information is sufficiently accurate for researcher validation.

The system runs reliably with minimal operational overhead.

Signal-to-noise ratio is acceptable and improvable through iteration.

Long-Term Vision

In the long term, Kommunal Grundsalg Monitoring could evolve into a broader “Municipal Signal Engine” within Resights, continuously identifying high-value public-sector real estate events and transforming unstructured public information into structured, actionable data.