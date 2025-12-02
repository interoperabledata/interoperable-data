# Interoperable Data

The **Interoperable Data** project provides an open, public, vendor-neutral framework for describing, transforming, and exchanging real-world business and domain data using simple JSON Schemas and small, composable functions.

This project is designed for **non-technical business users** as well as developers. Its goal is to make practical data movement—across industries and systems—simple, transparent, and accessible.

At a high level, the project includes:

- **A public catalogue of JSON Schemas** for common business documents (invoices, receipts, purchase orders, expense reports) and domain entities (patients, diagnoses, shipments, securities, etc.).
- **A library of tiny functions**, each with a minimal `manifest.json`, that transform or validate data using those schemas.
- **A local runner (`run/run.py`)** which executes user-defined workflows from a simple `workflow.id` file—copying data between channels and running functions in sequence.
- **A clear, predictable folder and naming structure** for all schemas so contributors can extend the system globally and consistently.

This repository is intentionally minimal. There are no servers, no cloud services, no containers. Users simply:

1. Drop files into `./run/inputs/`
2. Define steps in `workflow.id`
3. Run the workflow using `python run/run.py`
4. Pick up results in `./run/outputs/`

The entire system is offline-first, deterministic, and approachable—even for people who do not write code.

Below is the project’s schema naming and folder convention, which all schemas must follow.

## Schema Folder & Naming Conventions

This project follows a clear, predictable, and internationally scalable structure for organising JSON Schemas. It avoids ambiguity, enforces consistency, and aligns with patterns used by major platforms (Salesforce, FHIR, GS1, UN/CEFACT).

---

## 1. Folder Types

There are three kinds of folders, each with its own naming rules:

### **1. Taxonomy folders** (organise categories)

- **lowercase**
- **snake_case** for multi‑word names
- represent structural grouping, not domain concepts

Examples:

```
schemas/
documents/
entities/
healthcare/
financial_services/
supply_chain/
```

---

### **2. Concept folders** (represent actual business entities or documents)

- **UpperCamelCase**
- match the conceptual model name
- one folder per concept

Examples:

```
Invoice/
ExpenseReport/
Patient/
Diagnosis/
PurchaseOrder/
Policy/
Claim/
```

---

### **3. Variant / context folders** (industry or subtype)

- **lowercase**
- describe context, not concepts
- used for industry extensions or specialised profiles

Examples:

```
generic/
healthcare/
retail/
logistics/
construction/
insurance/
```

---

## 2. Folder Structure Summary

```
schemas/
  documents/                 # taxonomy
    Invoice/                 # concept
      generic/               # variant
        Invoice.generic.1_0.json
      healthcare/
        Invoice.healthcare.1_0.json

    ExpenseReport/
      generic/
        ExpenseReport.generic.1_0.json

  entities/                  # taxonomy
    healthcare/              # taxonomy
      Patient/               # concept
        Patient.generic.1_0.json
      Diagnosis/             # concept
        Diagnosis.generic.1_0.json

    financial_services/
      Policy/
        Policy.generic.1_0.json
      Claim/
        Claim.generic.1_0.json
```

---

## 3. JSON Schema File Naming

Schema files follow this pattern:

```
<Concept>.<variant>.<major_minor>.json
```

Where:

- **Concept** = UpperCamelCase (e.g., Invoice)
- **variant** = lowercase (e.g., generic, retail)
- **major_minor** = version number like `1_0`

Examples:

```
Invoice.generic.1_0.json
Invoice.healthcare.1_0.json
Patient.generic.1_0.json
ExpenseReport.generic.1_0.json
```

---

## 4. `$id` Rules

Each schema’s `$id` is its canonical public URL:

```
"$id": "https://interoperabledata.org/schemas/documents/Invoice/generic/Invoice.generic.1_0.json"
```

This ensures global resolvability and predictable imports.

---

## 5. Rationale

- **Taxonomy folders** represent information architecture
- **Concept folders** represent domain models
- **Variant folders** represent specialisations or industry layers
- Mixed casing is intentional: it visually separates types of folders
- This pattern scales globally, avoids collisions, and aligns with major enterprise data models

---

## 6. Quick Rules Cheat Sheet

- Taxonomy: `lowercase` (`entities`, `documents`, `healthcare`)
- Concept: `UpperCamelCase` (`Invoice`, `Patient`, `Diagnosis`)
- Variant: `lowercase` (`generic`, `retail`, `healthcare`)
- Files: `<Concept>.<variant>.<version>.json`
- Schema IDs: full URL under `interoperabledata.org`

---

This structure keeps the project clean, predictable, and usable across all industries and document types.
