# **SpendSense: Software Requirements Specification and Architecture Requirements Baseline**

## **1\. Executive Summary**

The following document constitutes the Software Requirements Specification (SRS) and Architecture Requirements Baseline for the SpendSense application. SpendSense is conceptualized as a local, Python-based financial utility designed to ingest, categorize, and analyze standardized transaction records, ultimately identifying spending patterns and statistically significant anomalies. The primary developmental constraint governing this project is highly restrictive: the system must be implemented as a Minimum Viable Product (MVP) within a 2.5-day window by a developer possessing only beginner-level proficiency in Python and SQL.  
Consequently, this baseline applies a rigorous, evidence-based methodology to separate essential core functionality from speculative scope creep. Features that introduce excessive algorithmic complexity, require third-party network integrations, or demand advanced architectural paradigms have been systematically excluded. The requirements prioritize mathematical robustness through the deployment of the Modified Z-score for anomaly detection, strict financial data integrity via integer-based minor unit storage, and deterministic local persistence using SQLite. By resolving contradictory recommendations found in preliminary research and translating the necessary capabilities into testable, concrete requirements, this document removes ambiguity and provides a verified, actionable blueprint ready for the subsequent architecture design phase.

## **2\. Reviewed Source Documents and Research Method**

This specification synthesizes and reconciles findings from three preliminary input documents: the *SpendSense Architecture Decision Report*, the *SpendSense MVP Algorithm Research Plan*, and the *SpendSense MVP Technical Reference*. Because these foundational documents contained conflicting recommendations regarding statistical algorithms, data persistence strategies, and testing frameworks, their claims were subjected to a mandatory research-integrity protocol.  
The research methodology prioritized direct verification against authoritative primary sources. Statistical claims regarding anomaly detection methodologies were evaluated against the National Institute of Standards and Technology (NIST) Engineering Statistics Handbook, as well as the foundational robust statistics literature by Iglewicz and Hoaglin1. Technical capabilities were verified exclusively against the official documentation for Python, Pandas, SQLite, and established testing frameworks such as pytest and unittest4.  
Within this report, a strict separation is maintained between verified facts (supported by inspected sources), engineering recommendations (proposed decisions optimized for the beginner developer's constraints), and firm system requirements. The objective is not to design the final architecture, but to establish a thoroughly audited foundation of constraints, input/output contracts, and acceptance criteria that the eventual architecture must satisfy to guarantee a successful Wednesday delivery.

## **3\. Consolidated Project Goal and Intended User**

The primary project goal is to deliver a functional, locally executing Python application that ingests a standardized CSV of synthetic financial transactions, validates and cleans the data, categorizes expenses using transparent substring-matching rules, persists the records in a local SQLite database, and generates a human-readable summary report highlighting categorical spending totals and potential statistical anomalies.  
The intended user of this MVP is a beginner-level software engineering candidate demonstrating their technical aptitude during an internship interview or portfolio review. The specific task they need to complete is the flawless, end-to-end execution of a local data processing pipeline. The application must serve as a verifiable artifact of the user's understanding of fundamental software engineering concepts, including data validation, relational database operations, and robust statistical calculation. To satisfy this use case, the system must prioritize transparency, repeatability, and simplicity over enterprise-grade scalability, avoiding any reliance on external financial APIs, cloud infrastructure, or opaque machine learning models.

## **4\. Conflicts and Inconsistencies Across the Three Reports**

A critical review of the three existing SpendSense research reports revealed several material contradictions regarding the proposed implementation. The following analysis investigates these conflicts, evaluates the underlying evidence, and establishes the required behavior for the architecture design stage.

### **A. Anomaly Detection**

The preliminary reports presented conflicting recommendations for identifying unusual transactions. One report advocated for a simple threshold or standard-deviation Z-score, another specified the Modified Z-score using Median Absolute Deviation (MAD), and a third vaguely recommended a Z-score based on the mean.  
Standard statistical literature demonstrates that the classic Z-score, which relies on the sample mean and standard deviation, is highly susceptible to the "masking effect"1. In skewed financial data, a single massive transaction inflates the standard deviation, essentially widening the acceptable threshold and allowing extreme outliers to hide9. Conversely, the Modified Z-score replaces the mean with the median and the standard deviation with the Median Absolute Deviation (MAD)3. Because the median and MAD possess a 50% breakdown point, they are entirely robust against extreme values, making the Modified Z-score the superior choice for financial anomaly detection3. The system must implement an anomaly detector that is mathematically robust against masking. Therefore, it is an engineering recommendation that the MVP utilize the Modified Z-score. The precise implementation (e.g., using Python's statistics module) is deferred to the architecture phase.

### **B. Recurring-Payment Detection**

The reports conflicted on the necessity of detecting recurring payments, with one proposing a heuristic based on merchant identity, amount similarity, and date intervals, while another recommended deferring the feature.  
Evidence regarding the parsing of transaction data—particularly messy formats like those exported by major banks—indicates that timestamps are often omitted, narrations are cryptic, and value dates frequently drift due to weekends and holidays12. Building a reliable temporal heuristic that accounts for these variables without generating an overwhelming number of false positives requires complex algorithmic logic that exceeds the capacity of a beginner operating within a 2.5-day window. Consequently, recurring-payment detection is not essential to the core goal of demonstrating a working data pipeline and must be deferred as a post-MVP enhancement.

### **C. Transaction Deduplication**

Regarding duplicate imports, one report proposed generating a deterministic hash from the transaction date, merchant, and amount. Another warned that legitimate transactions frequently share these exact attributes, recommending a run-level replacement policy instead.  
Financial datasets frequently contain legitimate duplicate rows; for example, a consumer purchasing two identical coffees from the same merchant on the same day will generate two records with indistinguishable dates, descriptions, and amounts15. Utilizing a deterministic hash based on these three fields will silently discard legitimate economic activity, causing irrecoverable data loss and breaking the financial semantics of the application. The import behavior must therefore preserve identical rows. To prevent false duplicate detection when a user re-runs the application for demonstration purposes, the system requires a run-level isolation strategy—either by clearing the database prior to a fresh import or by assigning unique batch IDs.

### **D. Financial Semantics**

The input reports demonstrated ambiguity regarding financial signs, with some sections treating expenses as negative values and income as positive, while others conflated refunds with general income.  
Real-world bank statements utilize wildly inconsistent formats. Some banks utilize separate debit and credit columns, while others employ a single column with positive and negative signs, or even Indian numbering formats (e.g., "1,50,000") that break standard CSV parsers12. To eliminate ambiguity, the application must define a strict, precise data contract for the MVP rather than attempting to parse all universal formats. Expenses must be mathematically isolated from income. Treating a refund identically to income artificially inflates revenue metrics rather than offsetting the respective expense category. The required calculations must explicitly define how Debits and Credits are aggregated, which must be finalized prior to schema design.

### **E. Database Persistence**

Contradictions existed regarding whether the SQLite database should function as a single persistent table for raw transactions or whether it should store pre-calculated spending summaries and derived results.  
Relational databases are inherently designed to store normalized raw data and compute aggregations dynamically17. Storing derived mathematical summaries introduces the risk of state de-synchronization—if a raw transaction is altered or deleted, the persisted summary becomes stale and invalid. Therefore, the system only needs to retain the raw, cleaned transaction records. All spending totals, categorical groupings, and anomaly detections must be computed dynamically at runtime when the report is generated.

### **F. Testing Framework**

The reports were split between recommending pytest and Python's built-in unittest framework.  
The pytest framework offers significant advantages in simplicity, utilizing standard Python assert statements and automated test discovery, which dramatically reduces the cognitive load for beginners6. Conversely, unittest requires object-oriented boilerplate (e.g., creating classes, using self.assertEqual), but it is included within the Python Standard Library5. This satisfies the constraint of minimizing external dependencies. Both frameworks are capable of verifying the application's correctness. The requirement is simply that core logic must be testable and verified; the selection of the specific framework is an unresolved decision deferred to the architecture design stage.

### **G. Delivery Scope**

Finally, the reports conflicted on the overall delivery scope, ranging from a minimal Command Line Interface (CLI) application to a broader portfolio suite featuring graphical dashboards.  
Given the rigid 2.5-day delivery deadline and the developer's beginner constraints, any feature that does not directly contribute to the ingestion, storage, or mathematical analysis of the data introduces unacceptable risk. Advanced graphical interfaces and portfolio-level enhancements must be separated from the Wednesday deliverable. The MVP is strictly defined as a minimal, local CLI application.

## **5\. Recommended Scope Boundaries**

To guarantee delivery by the Wednesday deadline, the scope of SpendSense must be aggressively constrained.

### **5.1 Intended Core Use Case**

The primary end-to-end user journey involves the developer utilizing the application to demonstrate backend engineering fundamentals. The user will place a synthetic, standardized CSV file containing transaction data into a designated local directory. They will execute the application via the command line. The system will ingest the CSV, validate the formatting, normalize the merchant descriptions, and apply rule-based categorization. The system will then write the valid transactions to a local SQLite database, dynamically calculate categorical spending totals, execute the anomaly detection algorithm to flag unusual transactions, and print a formatted text report to the terminal.

### **5.2 MVP Boundary**

The capabilities strictly required for the Wednesday demonstration include:

* Ingestion of a single, well-defined CSV data contract.  
* Row-level data validation and error handling for missing or malformed fields.  
* Deterministic, rule-based categorization utilizing exact substring matching.  
* Dynamically calculated expense summaries grouped by category.  
* Potential anomaly detection utilizing the mathematically robust Modified Z-score.  
* Local persistence of raw records using SQLite.  
* A terminal-based summary report indicating parsing success, totals, and flagged outliers.

### **5.3 Post-MVP Boundary**

Useful enhancements that provide value but threaten the 2.5-day deadline include:

* Recurring-payment detection heuristics.  
* Support for multiple, varying real-world bank CSV formats.  
* Exporting analytical reports to PDF or external spreadsheet files.  
* Advanced graphical user interfaces or web dashboards (e.g., Streamlit).

### **5.4 Explicit Exclusions**

The following capabilities are deliberately excluded from the MVP. Attempting to implement them would violate the project's learning burden and deadline constraints:

* **External financial APIs (e.g., Plaid):** Excluded to eliminate network latency, authentication complexity, and external points of failure.  
* **Bank authentication or credential storage:** Excluded to ensure absolute data privacy and eliminate security liability. The application must use synthetic data only.  
* **Cloud hosting and cloud databases:** Excluded to maintain a purely local, reproducible execution environment that requires zero infrastructure provisioning.  
* **Machine-learning classifiers:** Excluded because training robust classification models requires substantial labeled datasets and tuning expertise that vastly exceeds beginner capabilities and the available timeframe20.  
* **Complex database locking or concurrency optimizations:** Excluded because the application will operate as a single-threaded local script. Advanced Write-Ahead Logging (WAL) concurrency is unnecessary and creates sidecar files (-wal, \-shm) that complicate local directory management22.

## **6\. Functional Requirements**

The following numbered, testable functional requirements define the exact behavior the finished system must exhibit.

### **FR-A. CSV Input**

* **FR-A001 (Single Input Contract):** The system shall ingest financial data from a single, predefined CSV schema. *Priority: Must. Rationale: Supporting infinite bank layouts is impossible within the deadline.*  
* **FR-A002 (Required Headers):** The system shall require the input CSV to contain headers mapping to Date, Description, Amount, and Type. *Priority: Must. Rationale: Minimum data required for semantic analysis.*  
* **FR-A003 (Empty File Handling):** The system shall detect an empty input file, abort the execution gracefully, and log an understandable error message. *Priority: Must. Verification: AT-12.*  
* **FR-A004 (Missing File Handling):** The system shall detect the absence of the target CSV file and halt execution with an explicit warning rather than throwing a raw Python stack trace. *Priority: Must.*

### **FR-B. Validation and Cleaning**

* **FR-B001 (Row-Level Validation):** The system shall evaluate each row independently. If a row contains an invalid date, a non-numeric amount, or is entirely empty, the system shall skip the invalid row, log a warning, and continue processing the remaining valid rows. *Priority: Must. Rationale: A single malformed transaction must not silently discard the rest of a 500-row financial ledger. Verification: AT-03, AT-04.*  
* **FR-B002 (Whitespace Normalization):** The system shall strip leading and trailing whitespace from the merchant description strings prior to categorization and storage. *Priority: Must. Verification: AT-06.*

### **FR-C. Merchant Normalization and Categorization**

* **FR-C001 (Rule-Based Categorization):** The system shall assign a category to a transaction by evaluating the normalized description string against a predefined set of exact substring match rules. Priority: Must. Rationale: Explainable and deterministic without the overhead of machine learning21. Verification: AT-07.  
* **FR-C002 (Uncategorized Label):** The system shall assign the label "Uncategorized" to any transaction whose description does not match any predefined rule. *Priority: Must. Verification: AT-05.*  
* **FR-C003 (Rule Precedence):** The system shall enforce a deterministic evaluation order for categorization rules to resolve overlaps consistently. *Priority: Must.*

### **FR-D. Spending Summaries**

* **FR-D001 (Total Expenses):** The system shall calculate the sum of all valid transactions explicitly defined as expenses. *Priority: Must. Verification: AT-08.*  
* **FR-D002 (Categorical Expenses):** The system shall calculate and group total expenses by their assigned category. *Priority: Must. Verification: AT-10.*  
* **FR-D003 (Income Exclusion):** The system shall strictly exclude transactions defined as income or transfers from the total expense and categorical expense calculations. *Priority: Must. Verification: AT-09, AT-11.*

### **FR-E. Potential Anomaly Detection**

* **FR-E001 (Algorithm Implementation):** The system shall implement the Modified Z-score algorithm for anomaly detection1. *Priority: Must. Rationale: Statistically robust method required for financial distributions.*  
* **FR-E002 (Robust Spread Calculation):** The system shall calculate the sample median, compute the absolute deviations from the median for each point, and calculate the median of those deviations (MAD)3. *Priority: Must.*  
* **FR-E003 (Anomaly Flagging):** The system shall flag a transaction as a potential statistical anomaly if its absolute Modified Z-score exceeds a predefined threshold of 3.51. *Priority: Must. Verification: AT-13.*  
* **FR-E004 (Zero-Spread Safety):** The system shall evaluate the MAD prior to Z-score calculation. If the MAD equates to zero (meaning more than 50% of the dataset values are identical), the system shall bypass the division operation to prevent a runtime crash and shall not flag anomalies for that dataset10. *Priority: Must. Verification: AT-15.*  
* **FR-E005 (Minimum Sample Size):** The system shall restrict anomaly detection to datasets containing a minimum of 5 valid expense transactions. Priority: Must. Rationale: Statistical outliers lack mathematical meaning in exceptionally small samples27. Verification: AT-14.

### **FR-F. Possible Recurring-Payment Detection**

* **FR-F001 (Recurrence Logic):** *Priority: Out of Scope.* The feature is deliberately deferred to protect the core MVP delivery deadline.

### **FR-G. SQLite Persistence**

* **FR-G001 (Raw Data Storage):** The system shall persist all valid, imported transactions into a local SQLite database. *Priority: Must. Verification: AT-01.*  
* **FR-G002 (Dynamic Aggregation):** The system shall retrieve raw transactions and calculate all spending summaries dynamically. It shall not persist derived totals in the database schema. *Priority: Must.*  
* **FR-G003 (Duplicate Prevention):** The system shall prevent the false duplication of records upon consecutive executions of the same file. It shall achieve this via a run-level replacement policy (e.g., dropping and recreating the table upon application start) to support repeatable demonstrations. *Priority: Must. Verification: AT-18.*

### **FR-H. Report Generation**

* **FR-H001 (End-to-End Report):** The system shall generate and print a text-based analytical report to the console. *Priority: Must. Verification: AT-21.*  
* **FR-H002 (Report Metrics):** The report shall explicitly list the total number of records parsed, the count of accepted rows, the count of rejected rows, the categorical spending totals, and a distinct list of any transactions flagged as statistical anomalies. *Priority: Must.*

### **FR-I. Testing and Documentation**

* **FR-I001 (Logic Verification):** The system's core mathematical and categorization functions shall be verified via an automated test suite. *Priority: Must.*  
* **FR-I002 (Repeatable Setup):** The repository shall contain a README document providing explicit, step-by-step instructions for initializing the Python environment, installing required libraries, and executing the application. *Priority: Must. Verification: AT-22.*

## **7\. Non-Functional Requirements**

To ensure the MVP remains focused, operable, and maintainable by a beginner, the following non-functional requirements dictate the system's operational constraints.

* **NFR-A. Simplicity:** The software architecture must utilize procedural or basic object-oriented paradigms. It must avoid advanced abstractions (e.g., asynchronous I/O, complex metaclasses, distributed event buses) so that the developer can confidently explain the entire execution flow during an interview.  
* **NFR-B. Local Execution:** The complete workflow—from CSV ingestion to report generation—must operate locally on the host machine without relying on external remote services, cloud databases, or third-party analytical APIs.  
* **NFR-C. Reliability:** The system's financial calculations must be impervious to floating-point arithmetic inaccuracies (e.g., the binary representation error where 0.1 \+ 0.2 \= 0.30000000000000004). Validated integer math must be utilized28.  
* **NFR-D. Reproducibility:** The application state must be easily resettable. The SQLite database file must be capable of being deleted and seamlessly rebuilt from the source CSV in subsequent executions without complex migration scripts.  
* **NFR-E. Testability:** The data-processing algorithms (categorization logic and Modified Z-score calculations) must be decoupled from the database I/O layer, allowing them to be tested using isolated, synthetic data structures in memory.  
* **NFR-F. Data Privacy:** The application must not process, ingest, or store authentic personal banking credentials. The required demonstration data must be entirely synthetic or rigorously anonymized.  
* **NFR-G. Maintainability:** Categorization rules and threshold constants (such as the 3.5 anomaly multiplier) must be isolated in a centralized configuration dictionary or constant block, preventing the need to modify core logic when updating rules.  
* **NFR-H. Performance:** Given the MVP boundary focuses on small, synthetic CSV files, specific microsecond throughput targets are unnecessary. The application must simply execute the end-to-end pipeline in a reasonable timeframe (under 5 seconds for a standard demonstration file).  
* **NFR-I. Delivery Feasibility:** The combined scope of the functional requirements must be implementable, verifiable, and documentable within 2.5 days (roughly 20 focused engineering hours).

## **8\. Transaction Data Contract**

Real-world financial institutions employ drastically varying CSV formats. Some merge amounts into a single column, others separate debits and credits, and international formats utilize irregular comma placements (e.g., the Indian lakh format "1,50,000")12. Attempting to build a universal parser within 2.5 days is impossible. Therefore, the MVP will define its own explicit data contract.

### **Proposed Standard Input CSV Schema**

| Column Header | Accepted Format | Validation Rule |
| :---- | :---- | :---- |
| Date | String | Must adhere to ISO-8601 (YYYY-MM-DD). |
| Description | String | Must not be empty or solely whitespace. |
| Amount | Float | Represents the monetary value as a standard float. Must be positive in the CSV. |
| Type | String | Must evaluate exactly to DEBIT or CREDIT. |

### **SQLite Persistence Schema and Precision Strategy**

To satisfy **NFR-C (Reliability)**, financial amounts must not be stored using floating-point REAL data types in SQLite. Due to the limitations of IEEE 754 binary floating-point representation, fractional monetary values cannot be stored exactly, leading to rounding errors during aggregation17.  
The system shall convert the parsed CSV float amounts into integer minor units (e.g., multiplying by 100 to represent cents or paise) immediately upon ingestion, and store these integers in SQLite29.  
**Required SQLite Table Definition:**

* id (INTEGER PRIMARY KEY)  
* transaction\_date (TEXT)  
* description (TEXT)  
* amount\_minor\_units (INTEGER)  
* transaction\_type (TEXT)  
* category (TEXT)

## **9\. Data-Processing and Financial-Semantic Requirements**

The system must clearly distinguish between types of cash flow to prevent mathematical distortion in the summary reports.

* **Expense Semantics:** Any transaction containing the Type string DEBIT shall be mathematically treated as an expense. Its integer minor unit value is conceptually positive for summation purposes.  
* **Income Semantics:** Any transaction containing the Type string CREDIT shall be mathematically treated as income.  
* **Refund Treatment:** Advanced refund matching (linking a specific CREDIT back to a previous specific DEBIT to offset a category) requires complex temporal entity resolution. For the Wednesday MVP, all refunds are broadly classified as Income.  
* **Transfer Treatment:** If a transaction description matches a rule classifying it as a "Transfer", its monetary value must be explicitly excluded from both the total expense sum and the anomaly detection baseline, as transfers do not represent true economic spending.  
* **Invalid Row Behavior:** As defined in FR-B001, if a row lacks a required field, contains a malformed date, or an unparseable amount, it is flagged as an invalid row. The system must drop the specific row, log it, and continue parsing the file. It must not silently merge corrupted data into the financial totals.

## **10\. Anomaly-Detection Requirements**

Anomaly detection is an essential demonstration of the application's analytical capability. It must operate using strict mathematical definitions, not subjective heuristic guesswork.

* **Comparison Baseline:** A transaction is evaluated exclusively against the population of other valid expense transactions. Income and transfers are removed from the baseline prior to calculation.  
* **The Algorithm:** The system shall utilize the Modified Z-score. The standard Z-score relies on the mean and standard deviation, which have a 0% breakdown point. A single massive transaction (e.g., buying a car) inflates the standard deviation, raising the threshold so high that other legitimate outliers are "masked" and go undetected7. The Modified Z-score avoids this masking effect entirely3.  
* **Calculation Steps:**  
  1. Extract all valid expense amounts (in minor units) into an array ![][image1].  
  2. Compute the median of the array, denoted as ![][image2].  
  3. Compute the absolute deviation of every individual transaction from the median: ![][image3].  
  4. Compute the Median Absolute Deviation (MAD), which is the median of all absolute deviations ![][image4]3.  
  5. Calculate the Modified Z-score for each transaction using the standard adjustment constant (0.6745, which scales the MAD to estimate standard deviation for normal data): ![][image5]1.  
* **Zero-Spread Handling:** If more than 50% of the transactions are identical, the MAD will be zero10. The system must catch this state before division to prevent a ZeroDivisionError. If MAD is zero, anomaly detection is bypassed.  
* **Explanation and Distinction:** A flagged result (![][image6]) is labeled strictly as a "Statistical Anomaly." The system shall not classify these as "fraud." A legitimate, expected large transaction (e.g., annual rent) will correctly be flagged because it represents a mathematical deviation from daily spending7.

## **11\. Recurrence-Detection Requirements**

As investigated during the conflict resolution phase (Section 4B), building a heuristic to detect recurring payments from sparse, noisy CSV data introduces high algorithmic complexity and severe false-positive risks32. Given the hard constraints of a beginner developer and a 2.5-day delivery window, **Recurring-Payment Detection is definitively Out of Scope.**

## **12\. Database Persistence Requirements**

* **Technology Constraint:** The system shall utilize Python's built-in sqlite3 library.  
* **Concurrency and Journaling:** SQLite offers advanced Write-Ahead Logging (WAL) for high concurrency. However, WAL mode creates persistent shared-memory (-shm) and log (-wal) sidecar files in the local directory22. Because SpendSense is a single-threaded CLI application executing sequentially, high concurrency is unnecessary. The standard rollback journal mechanism is perfectly adequate, ensuring atomic transactions while keeping the directory clean of sidecar files22.  
* **State Management:** The MVP does not require historical delta tracking across multiple distinct import sessions. To ensure idempotency and prevent duplicate data accumulation during iterative testing and demonstrations, the application must execute a destructive load strategy (e.g., executing DROP TABLE IF EXISTS followed by CREATE TABLE) at the initiation of the processing pipeline.

## **13\. Technology Capability Requirements**

The architecture must restrict itself to a minimal footprint. The following technical capabilities have been verified against official documentation:

| Technology | Required Capability | Justification | Verified Source | Dependency Status |
| :---- | :---- | :---- | :---- | :---- |
| **Python 3.x** | Core logic, string parsing, arithmetic. | Meets beginner constraints. The built-in statistics.median fulfills the MAD mathematical requirements. | Python Official Docs | Built-in |
| **SQLite3** | Relational persistence, aggregation queries (SUM, GROUP BY). | Provides reliable local database capabilities without requiring a server daemon installation. | SQLite Docs4 | Built-in |
| **CSV Module** or **Pandas** | Ingestion and parsing of flat CSV files. | Needed to read input. *Unresolved decision:* csv module requires zero dependencies34, while Pandas offers robust type parsing35 at the cost of a heavy external library. | Python Docs / Pandas Docs | Open for Architecture |
| **Unittest** or **Pytest** | Automated verification of calculations. | Necessary to satisfy NFR-E. *Unresolved decision:* unittest is built-in5, but pytest minimizes cognitive load18. | Pytest Docs6 | Open for Architecture |

## **14\. Acceptance-Test Matrix**

The finished system's adherence to the requirements shall be verified against the following traceable scenarios.

| Test ID | Req ID | Initial State / Input | Action | Expected Outcome | Verification Method | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **AT-01** | FR-G001 | Valid CSV with 5 well-formed rows. | Execute import. | 5 valid rows are successfully stored in SQLite. | SQL COUNT(\*) query | Mathematically checked |
| **AT-02** | FR-A002 | CSV file missing the required 'Amount' column. | Execute import. | System aborts gracefully with a clear error message. | Script exit code & Console log | Implementation run |
| **AT-03** | FR-B001 | CSV contains a row with 'invalid-date' instead of YYYY-MM-DD. | Execute import. | The specific row is skipped; warning is logged; other valid rows import successfully. | SQL COUNT(\*) & Log inspection | Implementation run |
| **AT-04** | FR-B001 | CSV contains a row with a non-numeric amount (e.g., 'Fifty'). | Execute import. | The specific row is skipped; warning is logged. | SQL COUNT(\*) | Implementation run |
| **AT-05** | FR-C002 | CSV contains a transaction from merchant "UNKNOWN SHOP" with no corresponding rule. | Categorize transaction. | Category is assigned as "Uncategorized". | Unit test assertion | Mathematically checked |
| **AT-06** | FR-B002 | CSV contains a merchant string with padding: " UBER ". | Clean and categorize. | String is normalized to "UBER" and categorized correctly based on rules. | Unit test assertion | Mathematically checked |
| **AT-07** | FR-C003 | Dictionary contains overlapping rules for "AMAZON" and "AMAZON PRIME". | Categorize "AMAZON PRIME". | A predictable, deterministic rule is applied based on defined precedence. | Unit test assertion | Mathematically checked |
| **AT-08** | FR-D001 | 3 DEBIT transactions processed with amounts: 100, 200, 300\. | Compute total summary. | Total expense output equals 600\. | Unit test assertion | Mathematically checked |
| **AT-09** | FR-D003 | 2 DEBIT transactions (100, 200\) and 1 CREDIT transaction (500) processed. | Compute total summary. | Total expense output equals 300 (Income excluded). | Unit test assertion | Mathematically checked |
| **AT-10** | FR-D002 | 2 DEBIT transactions categorized as "Food" (10, 20), 1 as "Transit" (50). | Compute categorical summary. | Output shows Food: 30, Transit: 50\. | SQL GROUP BY output | Implementation run |
| **AT-11** | FR-D003 | A CREDIT transaction classified specifically as a "Refund". | Compute total summary. | Transaction is treated broadly as Income, offsetting no specific expense for the MVP. | Unit test assertion | Mathematically checked |
| **AT-12** | FR-A003 | The provided CSV file is entirely empty. | Execute import. | Process aborts with a specific "File is empty" warning. | Console output | Implementation run |
| **AT-13** | FR-E003 | Dataset containing 1 extreme outlier (e.g., 10, 12, 10, 11, 10, 500). | Run anomaly detector. | The value '500' is successfully flagged as an anomaly. | Unit test assertion | Mathematically checked |
| **AT-14** | FR-E005 | Dataset containing only 3 transactions. | Run anomaly detector. | Anomaly detection is intentionally bypassed due to insufficient sample size. | Unit test assertion | Implementation run |
| **AT-15** | FR-E004 | Dataset with zero spread (e.g., 10, 10, 10, 10, 10). | Run anomaly detector. | Function returns gracefully; division by zero error is avoided. | Unit test assertion | Mathematically checked |
| **AT-16** | FR-E001 | A legitimate, high-value transaction (e.g., annual Rent payment) exists in the data. | Run anomaly detector. | The transaction is mathematically flagged as a statistical anomaly (Expected behavior). | Unit test assertion | Mathematically checked |
| **AT-17** | N/A | Repeated merchant transactions with ambiguous recurrence intervals. | Check recurrence. | N/A (Deferred to post-MVP). | N/A | Post-MVP |
| **AT-18** | FR-G003 | Run the import pipeline twice sequentially using the exact same CSV file. | Re-execute script. | Database contains only one set of records (run-level isolation prevents false duplicates). | SQL COUNT(\*) | Implementation run |
| **AT-19** | FR-C001 | Two distinct, legitimate transactions with identical dates, descriptions, and amounts in the same CSV. | Execute import. | Both identical transactions are preserved and stored in the database. | SQL COUNT(\*) | Implementation run |
| **AT-20** | NFR-C | CSV contains a float amount of 10.50. | Write to database. | Amount is safely converted and stored as integer minor units 1050\. | SQL SELECT amount | Mathematically checked |
| **AT-21** | FR-H001 | Valid synthetic CSV data is provided in the input directory. | Full end-to-end execution. | A formatted text report is printed to the console containing all required metrics. | Visual inspection | Implementation run |
| **AT-22** | FR-I002 | A fresh, blank Python environment is initialized. | Follow README instructions. | Application runs successfully without missing dependency errors. | Manual execution | Implementation run |

## **15\. Requirements Traceability Matrix**

Every mandatory requirement must demonstrably support the core project goal.

| Goal ID | User Problem | Requirement ID | Required Behavior | Acceptance Test ID | Evidence or Rationale | Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| G-1 | Overlooking basic spending patterns. | FR-D002 | Calculate and group expenses by assigned category. | AT-10 | Categorization provides the foundational context of a financial tracker. | Confirmed |
| G-2 | Unnoticed unusual transactions. | FR-E001 | Detect statistical anomalies utilizing the robust Modified Z-score. | AT-13, AT-15 | Modified Z-score is heavily resistant to outlier masking compared to standard standard deviation thresholds3. | Confirmed |
| G-3 | Inconvenience of messy CSV formats. | FR-B001 | Validate records row-by-row, gracefully skipping malformed data. | AT-03, AT-04 | Ensures data ingestion resilience; a single typo must not halt the pipeline. | Confirmed |
| G-4 | Need for private, repeatable review. | FR-G001 | Local persistence of records within SQLite. | AT-01 | Eliminates reliance on external cloud databases, satisfying NFR-B. | Confirmed |
| G-5 | Ambiguous financial definitions. | FR-D003 | Strictly exclude identified income and transfers from expense totals. | AT-09, AT-11 | Explicit semantics prevent the artificial deflation of spending metrics. | Confirmed |
| G-6 | Technical calculation errors. | NFR-C | Store monetary values strictly as integer minor units. | AT-20 | Prevents pervasive IEEE 754 floating-point arithmetic errors28. | Confirmed |
| *G-7* | *Overlooking recurring payments.* | *FR-F001* | *Identify subscriptions and repeating patterns.* | *AT-17* | *Temporal heuristics are highly fragile and risk the tight delivery deadline.* | *Out of Scope* |

## **16\. Deadline Feasibility Assessment**

The critical constraint is the 2.5-day (approx. 20-hour) implementation window assigned to a beginner-level developer.

| Feature | Learning Required | Implementation Difficulty | Testing Difficulty | Fit for Deadline | Recommended Priority |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **CSV Parsing & Validation** | Low (Basic Python file I/O or Pandas) | Low | Low | Yes | Must |
| **Rule-based Categorization** | Low (Dictionary traversal, string matching) | Low | Low | Yes | Must |
| **SQLite Setup & Storage** | Medium (SQL CREATE, parameter binding) | Low | Medium | Yes | Must |
| **Mathematical Summaries** | Low (SQL GROUP BY or Python iterators) | Low | Low | Yes | Must |
| **Modified Z-score Anomaly** | Medium (Translating MAD equations into code) | Medium | Medium | Yes | Must |
| **Float to Integer Parsing** | Low (Multiplication logic) | Low | Low | Yes | Must |
| **Recurring Payment Logic** | High (Temporal spacing, fuzzy matching) | High | High | No | Out of Scope |

## **17\. Must/Should/Could/Out-of-Scope Prioritization**

* **Must:** Ingestion of a fixed CSV schema, row-level validation ensuring invalid data is skipped and logged, conversion of float amounts to integer minor units, exact-match substring categorization, dynamic generation of category summaries, Modified Z-score anomaly detection, SQLite local storage with run-level idempotency, CLI report generation, and automated unit testing for core logic.  
* **Should:** Incorporate mathematical safeguards for zero-spread arrays (MAD=0) during anomaly detection to prevent catastrophic runtime division-by-zero errors.  
* **Could:** Utilize pytest instead of unittest to substantially reduce testing boilerplate and cognitive load, provided the developer is comfortable managing one external dependency (pending architectural decision).  
* **Out of Scope:** Recurring payment detection, fuzzy string matching, machine learning models, external financial APIs, cloud integrations, and dynamic parsing of multiple disparate bank CSV layouts.

## **18\. Verified Source Register**

To ensure the absolute accuracy of the requirements defined in this document, claims were verified against original technical and statistical documentation:

* **Statistical Robustness and Anomaly Detection:** The identification of the "masking effect" inherent to standard Z-scores—where extreme values artificially inflate the standard deviation and hide outliers—was verified against authoritative statistical literature, including the NIST Engineering Statistics Handbook (Section 1.3.5.17) and the foundational work of Iglewicz and Hoaglin1. The deployment of the Median Absolute Deviation (MAD), which possesses a resilient 50% breakdown point, and the accompanying 3.5 multiplier threshold for the Modified Z-score are derived directly from these verified statistical frameworks3.  
* **Floating-Point Precision:** The requirement to convert float values to integer minor units (e.g., cents) before database insertion is supported by established computer science principles addressing IEEE 754 binary representation limitations. Official Python documentation concerning floating-point arithmetic explicitly notes that decimal fractions cannot be represented exactly, validating the necessity of integer mathematics for financial reliability28.  
* **Database Concurrency and Journaling:** The specification for SQLite persistence was evaluated against the official SQLite documentation. While Write-Ahead Logging (WAL) provides superior concurrency, the documentation confirms that traditional rollback journals are the default and are perfectly adequate for single-threaded applications. Using standard rollback avoids the creation of persistent \-wal and \-shm shared-memory files, which satisfies the requirement for simplicity and clean local execution4.  
* **Testing Framework Analysis:** Comparisons between Python testing frameworks were verified. The built-in unittest module requires no installation but demands significant object-oriented boilerplate5. In contrast, pytest documentation and developer community consensus confirm its use of simple assert statements drastically reduces cognitive load, though it requires an external package installation6.

## **19\. Unresolved Decisions and Assumptions**

This document successfully constrains the required behavior of the system. However, the following specific technical choices remain deliberately unresolved and must be decided during the Architecture Design stage:

> 1. **Data Ingestion Library:** Will the architecture utilize Python's built-in csv module (satisfying the zero-dependency preference) or the pandas library (which offers vastly superior missing-value and dataframe handling at the cost of a heavy external dependency)?  
> 2. **Testing Framework:** Will the final implementation mandate unittest to strictly adhere to a built-in-only constraint, or will it accept pytest to accelerate the beginner developer's testing velocity?  
> 3. **Run-Level Data Isolation Strategy:** How specifically will the system ensure that running the script consecutively on the identical CSV does not duplicate SQLite records? Will the architecture mandate a destructive load (DROP TABLE IF EXISTS on startup) or the implementation of an append-only structure with explicit run/batch IDs?

## **20\. Final Architecture-Readiness Checklist**

This requirements baseline formally addresses the objectives set forth for the project. Before proceeding to the Architecture Design stage, the following criteria have been met:

> 1. **What must SpendSense do by Wednesday?** Ingest a standardized CSV, clean the data, categorize transactions via exact rules, detect statistical anomalies using a Modified Z-score, store raw data locally in SQLite, and output a terminal summary report.  
> 2. **What must it not do?** It must not attempt recurring-payment detection, utilize machine learning, integrate with external APIs, store real banking credentials, or attempt to parse universal bank statement formats.  
> 3. **What input and output contracts must it satisfy?** It must accept a strict CSV schema containing Date, Description, Amount, and Type, convert floats to integer minor units, and output a formatted terminal text report.  
> 4. **What correctness and safety conditions must it satisfy?** It must prevent IEEE 754 floating-point errors via integer math, isolate invalid rows without crashing the pipeline, and safely bypass division-by-zero errors when calculating anomalies on zero-spread datasets.  
> 5. **How will we verify that it works?** Through the execution of the 22 specific scenarios detailed in the Acceptance-Test Matrix, combining automated unit tests and full pipeline implementation runs.  
> 6. **Which technical choices are supported by verified evidence?** The use of the Modified Z-score (Iglewicz and Hoaglin) over standard deviation, integer minor unit persistence over SQLite REAL types, and standard rollback journaling over WAL mode for isolated local scripts.  
> 7. **Which decisions remain open for the architecture-design stage?** The selection of the CSV parsing library (csv vs. pandas), the testing framework (unittest vs. pytest), and the specific implementation strategy for run-level database clearing.

This document formally closes the requirements engineering phase. The constraints, contracts, and criteria defined herein are internally consistent, verified against authoritative sources, and fully cleared to serve as the foundation for the Architecture Design stage.*This is for informational purposes only. For medical advice or diagnosis, consult a professional.*

#### **Works cited**

> 1. 1.3.5.17. Detection of Outliers \- Information Technology Laboratory, [https\://www\.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)  
> 2. Model-based transcriptome engineering promotes a fermentative, [https\://pmc.ncbi.nlm.nih.gov/articles/PMC5127345/](https://pmc.ncbi.nlm.nih.gov/articles/PMC5127345/)  
> 3. MAD-Scaled Z-Score: Robust Outlier Detection Calculator, [https\://metricgate.com/docs/mad-scaled-z-score/](https://metricgate.com/docs/mad-scaled-z-score/)  
> 4. sqlite3 — DB-API 2.0 interface for SQLite databases — Python 3.15, [https\://docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)  
> 5. unittest — Unit testing framework — Python 3.15.0 documentation, [https\://docs.python.org/3/library/unittest.html](https://docs.python.org/3/library/unittest.html)  
> 6. How to use fixtures \- pytest documentation, [https\://docs.pytest.org/en/stable/how-to/fixtures.html](https://docs.pytest.org/en/stable/how-to/fixtures.html)  
> 7. Outliers in Statistics: Meaning, Detection Methods, and Real Examples, [https\://statisticsfundamentals.com/descriptive-statistics/outliers/](https://statisticsfundamentals.com/descriptive-statistics/outliers/)  
> 8. Outlier Detector & Visualizer | Interactive IQR & Z-Score Tool, [https\://statisticsfundamentals.com/visual-tools/outlier-detector/](https://statisticsfundamentals.com/visual-tools/outlier-detector/)  
> 9. Z-Score vs Modified Z-Score for Outliers \- MetricGate, [https\://metricgate.com/blogs/zscore-vs-modified-zscore/](https://metricgate.com/blogs/zscore-vs-modified-zscore/)  
> 10. Median Absolute Deviation (MADe) | Outlier Detection, [https\://mad-calculator.com/guides/median-absolute-deviation](https://mad-calculator.com/guides/median-absolute-deviation)  
> 11. Modified Z-Score (Iglewicz-Hoaglin Robust Outlier Score) \- MetricGate, [https\://metricgate.com/docs/robust-z-score-modified/](https://metricgate.com/docs/robust-z-score-modified/)  
> 12. HDFC Bank Statement to CSV & Excel \- Bankstatemently, [https\://bankstatemently.com/banks/in/hdfc/bank-statement](https://bankstatemently.com/banks/in/hdfc/bank-statement)  
> 13. Complete Guide to Bank Statement Import in Tally \- TallyConnects, [https\://tallyconnects.com/blog/bank-statement-import-tally](https://tallyconnects.com/blog/bank-statement-import-tally)  
> 14. Bank Statement Reconciliation Software — Auto-Clean HDFC, SBI, [https\://clearledger.co.in/bank-reconciliation](https://clearledger.co.in/bank-reconciliation)  
> 15. (PDF) Stabl: Blockchain Fault Tolerance \- ResearchGate, [https\://www\.researchgate.net/publication/384245796\_Stabl\_Blockchain\_Fault\_Tolerance](https://www.researchgate.net/publication/384245796_Stabl_Blockchain_Fault_Tolerance)  
> 16. Scaling a Hierarchical Coordination Fabric for Geo-Distributed, [https\://uwspace.uwaterloo.ca/bitstreams/13f6861b-3b93-4c59-80f7-efe540fece6c/download](https://uwspace.uwaterloo.ca/bitstreams/13f6861b-3b93-4c59-80f7-efe540fece6c/download)  
> 17. REAL vs NUMERIC in SQLite \- GeeksforGeeks, [https\://www\.geeksforgeeks.org/sqlite/real-vs-numeric-in-sqlite/](https://www.geeksforgeeks.org/sqlite/real-vs-numeric-in-sqlite/)  
> 18. Test-Driven Development as Learning a Craft \- zencraft.top, [https\://www\.zencraft.top/posts/test-driven-development-as-learning-a-craft-advanced-techniques-for-beginner-clarity](https://www.zencraft.top/posts/test-driven-development-as-learning-a-craft-advanced-techniques-for-beginner-clarity)  
> 19. Writing unit tests in Python: How do I start? \[closed\] \- Stack Overflow, [https\://stackoverflow.com/questions/3371255/writing-unit-tests-in-python-how-do-i-start](https://stackoverflow.com/questions/3371255/writing-unit-tests-in-python-how-do-i-start)  
> 20. Practical Natural Language Processing: A Comprehensive Guide to, [https\://dokumen.pub/practical-natural-language-processing-a-comprehensive-guide-to-building-real-world-nlp-systems-1492054054-9781492054054-h-1409126.html](https://dokumen.pub/practical-natural-language-processing-a-comprehensive-guide-to-building-real-world-nlp-systems-1492054054-9781492054054-h-1409126.html)  
> 21. Transforming Unstructured Text into Data with Context Rule Assisted, [https\://arxiv.org/pdf/2301.08549](https://arxiv.org/pdf/2301.08549)  
> 22. Write-Ahead Logging \- SQLite, [https\://www\.sqlite.org/wal.html](https://www.sqlite.org/wal.html)  
> 23. File Locking And Concurrency In SQLite Version 3, [https\://www\.sqlite.org/lockingv3.html](https://www.sqlite.org/lockingv3.html)  
> 24. (PDF) Transforming Unstructured Text into Data with Context Rule, [https\://www\.researchgate.net/publication/367339204\_Transforming\_Unstructured\_Text\_into\_Data\_with\_Context\_Rule\_Assisted\_Machine\_Learning\_CRAML](https://www.researchgate.net/publication/367339204_Transforming_Unstructured_Text_into_Data_with_Context_Rule_Assisted_Machine_Learning_CRAML)  
> 25. Multiple Desirable Methods in Outlier Detection of Univariate Data, [https\://pmc.ncbi.nlm.nih.gov/articles/PMC8801745/](https://pmc.ncbi.nlm.nih.gov/articles/PMC8801745/)  
> 26. Modified Z-Score (Median and MAD): Outliers Explained in 2 Minutes, [https\://www\.youtube.com/watch?v=UTw0QjvzVcU](https://www.youtube.com/watch?v=UTw0QjvzVcU)  
> 27. Outlier Detection Calculator Online \- IQR Z-Score MAD Free, [https\://8gwifi.org/outlier-detection-calculator.jsp](https://8gwifi.org/outlier-detection-calculator.jsp)  
> 28. decimal — Decimal fixed-point and floating-point arithmetic, [https\://docs.python.org/3/library/decimal.html](https://docs.python.org/3/library/decimal.html)  
> 29. Storing currency values: data types, caveats, best practices ·, [https\://cardinalby.github.io/blog/post/best-practices/storing-currency-values-data-types/](https://cardinalby.github.io/blog/post/best-practices/storing-currency-values-data-types/)  
> 30. Python Data Type Conversion: A Guide With Examples \- DataCamp, [https\://www\.datacamp.com/tutorial/python-data-type-conversion](https://www.datacamp.com/tutorial/python-data-type-conversion)  
> 31. Recognize outliers and data cleaning considerations \- Varsity Tutors, [https\://www\.varsitytutors.com/practice/subjects/biostatistics/lessons/outliers-and-data-cleaning](https://www.varsitytutors.com/practice/subjects/biostatistics/lessons/outliers-and-data-cleaning)  
> 32. Bank Statement Converter — Free PDF to Excel/CSV, [https\://bankstatementmagic.com/](https://bankstatementmagic.com/)  
> 33. Avoiding SQLITE\_BUSY during recovery \- SQLite User Forum, [https\://sqlite.org/forum/forumpost/7e4adf2b23](https://sqlite.org/forum/forumpost/7e4adf2b23)  
> 34. csv — CSV file reading and writing — Python 3.15.0 documentation, [https\://docs.python.org/3/library/csv.html](https://docs.python.org/3/library/csv.html)  
> 35. pandas.read\_csv — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.read\_csv.html](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAWCAYAAAAinad/AAAA/ElEQVR4Xu2Tuw4BQRSGjwQhCiWJQqlSSSQKnYJGQ6GXeACFRrOvQCJEotYolBIa4R2IVxCtROHyn8xZO+sWQ6PwJV92dv7dk9kzs0R/viULR7Cv2YEJyZM32QDWJLsjBsuwCY9wAUswpOUnuIc9WIFxyZ4ShBORxzYeOIdRbe4tIvAMLbnPweU1/QAutoJFuIFpd2zGgVTBLX1ZiOGecTHeYe9NZkQYtuCa3L0zxkdq6/naJqd3vClGcAGLVDEmQ6p3fL7yMvcWfI4acErqMxn7zPHqhjL3El5Nl9QLVVJFbXicgjvJA1p2R4HUQ7p1yfxw/CCfkfOL/fkVLuCGNfJ+S57WAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAWCAYAAAAinad/AAABD0lEQVR4XmNgwA+CgfgvEP8H4m9AvACIbwCxPpIaosFOIHYAYisgXsgAMdgbWcEoYBAG4qVAPAsNh0LlebDI9UPlMAAnEHsCcRwQ3wXi10BcAMTySPLPGCCxuxuIkxkgkUMQKDJANOUgiYEMDULiEw0YGSCGnQBifiCWAOJdKCpIBP+gOIIB4q0yVGnSAMhVINeBEivIIJBryQYgA0CGoYcdyQDkiu1AvJwBNezIAqBMDoo9FwZE2HmgqCASgAw4AmWDXAMLuylwFUQAFQaIIegJEZTmnjBADCQIQOEDSs0fgXgjAySlIwNBIN7GADFMFk0OBYgzQLIOLNZAeA8Qc0Plk9DkQPgTA5kF5ChABQCQ8T4EOA5i7QAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHUAAAAWCAYAAAD+ZNNIAAADrElEQVR4Xu2aW6hNURSGf7lE5H5JFEmi3ApvlEIol0JRKJ54OS8U5UHnRYTigRfXKFF4kkjSEQ+KknIrJBJRUopy9/+NNdtzz7322rez99rrnP3V3z5rzXVae8wx5hhjrrWBFmnyjfpH/aFuUQ+oPVRP/6IW2WEstYqaSh2mvlAHqd7+RS1aZBJFcf/wZDeiS9q+nDoTnuxG1Gz7RuptpJ/BWFpk3am7qZPUMU/7qMHR+LlgbC/VJxoTNds+jdpAPad+BWNpkXWnzqfWUVdhXa9sWYBcc3SA+gtbRGdhPvDpFNsXwm5yKRxIiaw71dGLOk89o0ZF53pQd2BdcTE6xfadsIjaFg6kRFdxqlgCm1utXLGaGpcbjqVq27XxHUn1haUJpd65eVekR5JTh1EDEo6bjUEwp16H9S+P8odjKWZ7UdQuq2h/pDpghfoT9YQanrssVeKcqrS1DNbQfaUuUJOp97AN/fbommZETpVeUzODsThC2xNR1Pyg5nnnjsJuuMU7VwlrKlQ5gRM6VRnlGjUxOp5DfYcFpSsd92D2NSMKOn1Hv7YmUZFTt8JSrVKu4yZsgjRRPtOptuBcowidOonajNxKXA+bJD0/HUgtjj4duk7XqONMQml7dJlSmq8mEygQ98MWk19bkyjbqYpiRXO4Ij8gPvWeoG4E5xpF6FQfTexpWLeurj0OrYYXsJSchILW7dFL6SIqr91qiFRD+8FqqqutpShmewEzYLVInz66kSapmiisF0lOVfApCN8heVuQNnLofVi3K7RCNddasaUoZnsBU6jPKOwc9VpoFjUBtjJXUleop7D/SYPQqSobmpAO5GrormhMG3o1e3oT4o71ekt7bq2QNFBJ24HChdIO++6uNyhG2U6VgXLWmOh4KCylvIHVDE2cHm+1w6LsFbU0urbRhE7V35qMI9TD6G/n1E3UKeSe1qgZWwFLv+U0JZ2FHKiGTivyJTU+b9S2kLLrN6zG+n1NSNlOFUpXj2H/pBuvhe1Pb8OecsiZarn1xZTiGjkpPqFTtX9Wur0MS2eqlWruFJTHkf9WQytWT3EUAOFKqReaJy0CBZuTsqLLdHHjktLzkOgan4qcKpRydRMX2UrH/rF7tNXISQkJnSoU2cooDte5xqEJ1JOcrBLaXjOKLqVkrY5Sub9exDm1ErQCRsC2ZQrSrFGL7bEsou7CfnoxOxhrFLU4VdlFr70OoXkfRpSiWtsTUWpLKuT1phanCtWpLP+oqyzb/wPjvser3j5gRgAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAVCAYAAACg/AXsAAABBUlEQVR4Xu2Tuw4BQRSGj4iEROIaChKRaDQUWjqNB1B5AJXaA3gDUUpQKZQi8Q5qFCJZCoVSopLgP2as3XHZXVH6kq/Ycya7+8+ZIfrjhD7cwj1cwbip64AavMCm2rCLC/bgCRaVnm1CcAY1mDC3rPHAKCzAI5xAr2nFB9awC33y+Swt6yssiMEdzBhqS3IYhXe/rdTeRcnBBonYOvfsSWORHEa5v8RvqPFkNBJRsrBq6L0kDw9KrUSPKBy1LutjuCDxYhM8jSmJrzO8uXM4gAE4gmlpisQUK3LtEzwh1i2fIzD4aN8Ywg6J0/w1GxJXgP82rPRsw9eAN7tFIupX8ATVc/Mbrt1JJ/TjWLUNAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJ4AAAAWCAYAAAAxZiXOAAAFZklEQVR4Xu2ae6ilUxjGH7nfYtAgykmkcZcol/lDIRJJFDEml1zKLUTxxyhJGCm5hcmR3IlyiUw5xR+K8I9MopBLQxKhUHh/vd87e31rr33O2fvsveccZz31dPa69J1vr/Ws97a2VFHRxvPGf40fGdcYt20PV1SMBvsZNzeeaLwuG6tYJFhl3Cvv3Mi43bhD3lnRxqbGU4wPGO/MxkpgDnOPadrHG1cbzzSeatzduKvcIqQ43Xhx83lH4wXGfRvymb5+sZnxhLxzRNjJ+LrxC+OvcsGDO4xfy90u6wiWG+9R9xpUJLjB+LBxa+M+xiPbwy2cYdzTeIDxA7nLuVYe76T8tJkXmJBv2I1NG3F+JZ/7l/F84ybNWD9gg8e9uUcZb0vaE8aDkzbgQExqfIdiQeIT4xFJ+2n5wuU4zPhZ8/ki48/GQ+QnHwEgJvhQ0w4gjLuM69UW3qNyK7hV09cveMen8s4xgAPKwcKq404fbA9vwEnGV+TzKwr4Rm3rhGViUXPca3wn7zRcadwuaV+jtvU6y3iJcUpt4d0aEzLsbbxZ3ZYMS3N20mbe+0l7nPjHeKE87OjlIfYwvmdclg9UOHB5CCHwu/HwpA3CNWLlwHHymCYN6hEbli0F4sF9I8wptYW3Vu6izpNb3VT8gHjpbnkMSRyVC/FS45NZ3+XNX/4PVgmLjGUN5M8YFM/I1+LAfCDD4/JQpKKAfoSHWAAiwVKGkACb8GHSBiQbIBceCc02zWcs1/fGK5p2CsRXEh3gWWxsAJdNDAqwzogSd7zLhhnSOclncJA8KSqR+KzkJjlgCO9P4y3toS7wfukazQmYTrI6zCjZDAXE6TIy4gBegLkfG++TB6TzBbnwflK3e1gid2ux0SHEdONZ4KmkvbPxBfkmYtXWycXAZmIpj5ZvYulZgX6EF9heHhJgEWfCIMJD3BSM31An1uuFoQqPE0RQfLU8KyttVICFvV6euTGXL8RizqdK949ylxTA7fEdU2A5SDoQEgixRHaHtXlNbeGxaSerLDw2BFfFxsezsFIpBnG1GAD2gjg1Eqbd5O+/0vhE0zco4p0A8SaxXhp35uB7Dt3V3iT/4ggqXEoOyhQE17gvXNN8BCcYa8YGX6VOrIVAXlSnEMrG3288V27tcY0cLMCpZ7NLFugy43fqlE6Wyp/J2pB0IPT0WYMmFzyXUABhcAh4RogEEArkQp0tflDn/VknrPnbTR8s3V6QXGB5ec+hgRNOqswp5R+XzCkLieg4mcxhMeYrEALXP70sd4DvhBUruZf91XbZM4E4j1gyhN0vSuUUxMo7Qgq+qXjZIyxvqVQ0ClBO4SAO9f9hFTj1UTxNM6cAafaWxsfUW5wVcwNxWG4Ze2GVxrcHiG1SIyggY25fkrvYsGZpIZQsblIeK+FK/jYem4xXDAds8Gw3N82kR42RXJkhMESH+KIUQPwWsRHXSVhAYqSwiATlg5hcMr8825qJs01cVlSOnXMCYiNoJHgMixa1L8SG6BAfQHAIL0/tOQlU/DcmPq8cO+dkcU8zPie3YFiXtepktggsFdmXxj/UvgsFlC/WZ30VFdOCTDatzZC5IDz6qBOl95bUeUp1sYqKvkBV/E21EwUyJYS3Wv4LjhT0k9VGjapfvKpOrWi2DDdf8T8BWdGz8kIpxcgQE0kGlg2XG2DsUPl9HuMxl0IjsSBiTecvNvCzqigql2qCFJ0Z+03+I4NeWK7ue2W8y5Q6t0VcVZL8fWt8pDNtYYDCKldjqWV5Nxnjzo663RbGl7N5QQqv3BKw0FH5X8wgzn1L3cKZkCdov2j6ElT88KA0h4POLUX6My7i8TXyW4cFgf8AwxeQu7NRVbgAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAWCAYAAACv8OArAAADwklEQVR4Xu2YS6hNURzGP3lEiCjvEimhPFKUmHiVPMozxUxRCiOUARJTA+/kkQwMSEoZSFoh8hgSA+qSCBkQEnl8n/9Z3bVXZ7/OOfdc3Xt/9Q32Wuvsvfa31/r//+sAXXTR0ekbNzSB/lS3uLEzcDhuaALnqOFxY2cgzex+1B7qVUVnqMGJEUmmUg9hY69QG5LdCf4Hs4fA5qB3KrrLRlDdozZFhixfEqSZ3ZOaRz2n/lBfqemJEa0MoK5Rv6lf1CpqdGJEkvY2ey51EzaPT9R7FDPcUV9gi+kk9Zj6QS0LxmSSZrbnNnULZviiqM+zlTpO/YSt7jza0+xp1LPgehz1hloQtKXhYD546UMtQbEP9Y8TcUPETmoT7OYHoj6hHTCFugQbsyLZXRWNLWL2TOoBNRElXigH/y5jKtcKlw62APLQik7b3YXIekhvaja1FDbBamNXUyOpFuojNSHRWx2HYmYLxchH1D2Y+fWarvvNCq6HUk+RnWM8bWr2KJiReoBitkv0Wr9ilz6IQohCjsq6PByKmy1k8GTqOsz4xcnuulgPW0jKO3nI7Bmw5x+DfbQ4YWaSZfZ8qgc1lnpLvQj6ZMB+ag4s1GjCh4L+LBzKmR0ynrpMrYWFsFpZR12EJfSi89bHbqF2wwqAD9R5lDirpJmtEKLJCB/XvlWutQq0orWyRQvSQ4hWZGyKQ+1mh+geR6l3KPHCESrblBdWxh0F8Dv+NVpzQCZpZstIF1xrnFavUPWhWO1RyZcWQk7BPlaIQ2PMFjJLlVA9oWUXShgW4He83l9RIJc0s/XjC8G1KhGZrdJJFUy4WsuEEOFQv9l+VesQtS3qy0KlXvxhfAGQVtoKhU3t3o1Bm+bwEvZb3SOXNLP1tRWLPb5k0kqdFLQr3BQt+TwO9ZmtFaj8UTZuK94r5Pgd6tHc8wzT7tQYJclelTYfRlQcqEjIJTZb21Jh4jO1Jmj3Nw5DgjKxJqqYF5onM/bCkkiYVD0O5cxWyXeHug87/ZWqAAL6UFepG0Gbj9k7kCwrZaxWbThPRw0LrnVeUIItfIKMzdZDQvmkp4eq7BJKRppwPFbGqm7V/ySSVt6Tym9CHIqZLVNlrqoAJdrQjFpRLrpLHYTtXp0mdeSOP+B36izsA3k2w2K7PDuNGk6QsdmNQiWjYv6RuAPFzd4OK/MajczRQlD5txDlKhnthOWw3yqElqKtzNaO0DZULBsU9TkUM7vD0VZmK6HqTymdQOPTmUOX2Q1HybTaVnPopGZviRuawD5qYNzYUfkL5arCeY9QWU4AAAAASUVORK5CYII=>