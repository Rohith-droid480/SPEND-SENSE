# **SpendSense Architecture Decision Report**

## **1\. Executive Recommendation**

The objective of the SpendSense project is to deliver a functional, offline Python application that ingests, cleans, categorizes, and analyzes personal financial transaction data to identify patterns and anomalies. Given the strict operational constraints—specifically, that the developer is a beginner in Python and SQL, and that a demonstrably working Minimum Viable Product (MVP) must be completed within approximately 2.5 days (by Wednesday)—the recommended approach is to adopt a strictly minimal, core-workflow-focused architecture.  
The analysis strongly recommends Architecture A, characterized as the "Minimum Viable Local Application." This architecture deliberately strips away advanced statistical methods, external application programming interface (API) integrations, and graphical user interfaces to focus entirely on a robust Extract, Transform, Load (ETL) pipeline. By limiting the technology stack to the Python Standard Library, SQLite1, and the Pandas data manipulation library, the developer minimizes context switching and avoids the steep learning curves associated with object-relational mappers, frontend reactive frameworks, or machine learning libraries. The primary pedagogical and engineering goal is to ensure the developer fully comprehends the sequential data flow, the mechanisms of persistent local data storage, and the programmatic logic governing rule-based categorization. Attempting to build portfolio-ready error handling, cross-dataset recurring payment detection, or a browser-based dashboard within a 2.5-day window introduces an unacceptable risk of project failure. Architecture A guarantees a reliable, end-to-end demonstrable application by Wednesday, establishing a solid programmatic foundation that can be incrementally expanded after the initial deadline has been successfully met.

## **2\. Exact Project Goal and Measurable Definition of Done**

The precise engineering goal of the SpendSense project is to implement a local, offline data pipeline that transforms raw, unstandardized bank transaction comma-separated values (CSV) files into structured, categorized, and queryable SQLite database records. This pipeline must culminate in the generation of a simple text-based analytical report that identifies basic statistical anomalies and summarizes spending behavior across defined categories, all without exposing the end-user to the underlying database operations or complex command-line arguments.  
To ensure the project remains tightly scoped to the Wednesday deadline, the system achieves the "Definition of Done" only when all of the following measurable criteria are demonstrably met.

| Component Area | Measurable Definition of Done Criteria |
| :---- | :---- |
| **Execution** | A single Python entry point script can be executed from the terminal without raising unhandled exceptions, accepting a file path to a sample CSV. |
| **Ingestion** | The system successfully reads the CSV file into memory, correctly ignoring or emitting warnings about malformed rows without terminating execution abruptly. |
| **Transformation** | The system standardizes string formats, converts date fields into proper datetime objects, and enforces a strict mathematical sign convention for all financial amounts. |
| **Categorization** | The application applies a transparent, dictionary-based ruleset to categorize at least 80% of synthetic transaction data into broad budget categories, leaving unrecognized items clearly marked as 'Uncategorized'. |
| **Anomaly Detection** | The system calculates basic statistical boundaries for categories and flags any transaction exceeding a pre-defined threshold (e.g., two standard deviations above the mean) as a potential anomaly. |
| **Persistence** | The processed, cleaned, and categorized data is persisted to a local SQLite database file using a safe run-level append or replace strategy. |
| **Reporting** | The application outputs a readable, plain-text summary report to standard output, detailing total spending per category and explicitly listing the flagged anomalies. |
| **Quality Assurance** | A minimal suite of automated tests successfully validates the core categorization logic and the mathematical correctness of the anomaly detection threshold without requiring external database connections. |

## **3\. Architecture Alternatives and Comparison**

To determine the most appropriate path forward for a beginner developer operating under a hard 2.5-day deadline, three distinct architectural paradigms were evaluated against the constraints of time, educational value, and system reliability.

| Evaluation Metric | Architecture A (Minimal Local) | Architecture B (Portfolio-Ready) | Architecture C (Extended Application) |
| :---- | :---- | :---- | :---- |
| **Core Workflow (CSV to SQLite)** | Fully Implemented | Fully Implemented | Fully Implemented |
| **Categorization Mechanism** | Simple Dictionary / Substring Matching | Regular Expressions \+ NLP | Machine Learning / External API |
| **Anomaly Detection** | Static Threshold / Z-score | Moving Averages / Interquartile Range | Drift Monitoring / Isolation Forests |
| **User Interface** | Terminal / Console Text Output | Streamlit Web Dashboard | Cloud-hosted Web Application |
| **Duplicate Import Handling** | Run-level overwrite / Drop and Replace | Hash-based row deduplication | Advanced entity resolution pipelines |
| **Estimated Implementation Time** | 18 – 24 Hours | 35 – 50 Hours | 80+ Hours |
| **Risk of Missing Deadline** | Low | High | Certain Failure |
| **Interview Explainability** | Excellent (Clear constraints and logic) | Good (If fully comprehended) | Poor (Likely relies on copied code) |
| **Maintainability for Beginner** | High | Moderate | Low |

Architecture C is immediately disqualified from consideration. Integrating external financial APIs, population stability indexes, automated notifications, and cloud hosting violates the core constraint of building a local, offline application. Furthermore, these features require persistent infrastructure, credential management, and authentication mechanisms that cannot be safely implemented, tested, or understood by a beginner in a matter of days. Attempting this route ensures absolute failure against the Wednesday deadline.  
Architecture B represents the ideal end-state for a long-term portfolio piece but fails the immediate deadline constraint. Features such as robust recurring payment detection require complex time-series grouping, timedelta calculations, and sophisticated duplicate-import handling. Implementing a Streamlit interface, while visually appealing, introduces a completely new framework paradigm centered around reactive state management. This will distract the developer from mastering foundational Python data structures, Pandas operations, and SQL queries. While highly desirable for a final resume piece, the required hours vastly exceed the approximately 20 working hours available.  
Architecture A is the optimal and recommended choice. It ruthlessly prioritizes the core ETL pipeline. By generating a terminal report instead of a graphical dashboard, the developer focuses entirely on data manipulation rather than user interface layout. By utilizing a simple Z-score or static threshold for anomalies, the mathematical logic remains entirely transparent and explainable during a technical interview. The architecture is deliberately constrained to ensure the developer experiences the satisfaction of completing a working, robust system, providing a stable foundation upon which the features of Architecture B can be built in the weeks following the initial deadline.

## **4\. Recommended Architecture Diagram**

The recommended architecture follows a strict, linear pipeline model, commonly referred to as a Directed Acyclic Graph (DAG) in data engineering, albeit implemented as a simple sequential Python script. By avoiding object-oriented class hierarchies and complex dependency injection frameworks, the procedural flow remains intuitive for a beginner while delivering robust, predictable data transformations.  
The pipeline begins with CSV Input, where raw text files are loaded into active memory. This data immediately flows into a Validation and Cleaning layer, acting as a strict boundary that normalizes dates, enforces numerical types, and strips extraneous whitespace from text. The sanitized data then moves to the Categorization engine, which maps text strings against predefined rules to assign budgeting labels. Once labeled, the dataset bifurcates into the Analysis phase: one process aggregates the data to calculate spending summaries, while another scans the granular transactions to identify anomalies. Both the enriched granular data and the aggregated metrics are then routed to SQLite Persistence, ensuring the analytical results are saved to disk. Finally, the pipeline terminates at the Report Generation layer, which queries the newly saved data and renders a readable summary directly to the user's terminal. Modifying this flow—such as attempting to categorize data before validating it, or attempting to save data before analyzing it—will introduce state-management complexities and is strongly discouraged.

## **5\. Component Responsibilities and Data Flow**

An exhaustive investigation of the 12 proposed system components reveals distinct tiers of necessity for the MVP. The following analysis evaluates every component based on its underlying mechanics, inputs and outputs, educational difficulty, and alignment with the Wednesday deadline.

### **5.1. CSV Ingestion**

The ingestion component is essential. The core problem it solves is reading unstructured, potentially messy external text data from a file system into active computer memory for processing. The inputs are raw CSV files, and the output is a structured tabular data format, specifically a Pandas DataFrame. The primary dependency is the Pandas library, explicitly utilizing the pandas.read\_csv function2. This dependency is highly justified; while the Python standard library's csv.DictReader is capable of parsing files into dictionaries3, Pandas provides vectorized operations and native SQL exporting that significantly reduce the required codebase size for a beginner.  
The implementation difficulty is moderate. The primary failure cases involve encoding errors (such as reading a UTF-16 file as UTF-8), missing header rows, and malformed lines containing too many commas. The developer must utilize parameters such as on\_bad\_lines='skip' or 'warn' within the pandas.read\_csv call to ensure the application logs the error but does not crash when encountering corrupted data2. Testing this component requires passing synthetic CSV files with deliberately malformed rows and verifying that the resulting DataFrame instantiates successfully with the expected number of valid records.

### **5.2. Data Validation and Cleaning**

Validation and cleaning act as a crucial boundary layer, ensuring that downstream components never attempt to process unexpected data types. The inputs are raw DataFrames directly from the ingestion step, and the outputs are strictly typed DataFrames free of null values in critical columns. This component is essential.  
The standard implementation relies heavily on Pandas type-casting functions, such as pandas.to\_datetime to force strict date parsing4. A major difficulty for beginners is the silent failure or misinterpretation of date strings. If pandas.to\_datetime encounters mixed date formats, it may incorrectly swap days and months depending on the locale. Another major failure case is the presence of null values (NaN) in monetary columns. The system must explicitly drop these rows or impute missing amounts to prevent mathematical operations from returning null results. Testing this layer requires feeding the system a DataFrame containing strings in numeric columns and irregularly formatted dates to verify that the validation layer raises appropriate, readable exceptions or cleans the data to a standardized baseline.

### **5.3. Merchant-Description Normalization**

Normalization solves the problem of identical merchants appearing under slightly different names due to store identifiers, dates, or transaction routing numbers appended to the string (e.g., "TARGET T-0092" versus "TARGET"). The input is a raw string column, and the output is a new, cleaned string column. This is essential for accurate categorization.  
Implementation is straightforward for a beginner utilizing Pandas string accessors, specifically Series.str.lower() and Series.str.replace()5. The main failure case is over-normalization, where distinct merchants are accidentally merged into one because a generic word was retained while specific identifiers were aggressively stripped. Testing involves verifying that a predefined array of messy, real-world merchant names maps exactly to a standardized, human-readable baseline array.

### **5.4. Explainable Rule-Based Expense Categorization**

This component algorithmically maps normalized merchant names to meaningful budget categories. The input is the cleaned merchant string, and the output is a populated 'Category' column. This component forms the functional core of the application and is strictly essential.  
The simplest, most explainable, and most maintainable method for a beginner is a dictionary mapping substrings to categories, evaluated across the DataFrame using the Series.str.contains method6. The implementation difficulty is relatively low, but the manual maintenance of the ruleset can become tedious as the dataset grows. A major failure case occurs when overlapping substrings cause silent miscategorization. For instance, if the rule "Mart" maps to "Convenience Store", but a transaction reads "Wal-Mart", the order of operations dictates the outcome. The logic must evaluate specific rules before general rules. Testing requires passing a known array of merchants and asserting that the output category array exactly matches the expected categories. Advanced machine learning approaches for categorization must be deferred, as they violate the explainability constraint and the strict deadline.

### **5.5. Spending Summaries and Category Totals**

To provide tangible value, the application must aggregate the categorized data into human-readable metrics. The input is the categorized DataFrame, and the output is an aggregated DataFrame or Series representing total sums. This is essential and solves the core user problem of understanding overall monthly or weekly spending.  
This aggregation is highly accessible for a beginner using the pandas.DataFrame.groupby method7. By grouping on the 'Category' column and applying a sum aggregation to the 'Amount' column, the developer can generate instantaneous financial summaries. Failure cases generally involve attempting to sum non-numeric columns or failing to account for positive versus negative numbers, which is mitigated by strict adherence to a sign convention during validation. Testing involves grouping a small, hand-calculated synthetic dataset and utilizing assertions to verify the programmatic sums match the manual calculations.

### **5.6. Potential Anomaly Detection**

Anomaly detection highlights unusual spending behavior, alerting the user to potential fraud or unexpected large expenses. The input is the categorized DataFrame, and the output is a filtered subset of rows flagged as anomalies. This is an essential feature of the MVP, provided the mathematical logic remains rigidly simple.  
Implementation should rely on a basic statistical threshold. For a beginner, calculating the mean and standard deviation of all expenses, and then flagging transactions that fall beyond two or three standard deviations from the mean, is both achievable and highly explainable in a technical interview setting. The main failure case is a lack of sufficient data; applying standard deviations to a dataset of three transactions yields meaningless bounds, potentially leading to false positives. Testing requires asserting that a deliberately oversized transaction in a synthetic dataset is successfully isolated by the anomaly filter.

### **5.7. Possible Recurring-Payment Detection**

This component aims to find subscription services by identifying identical amounts charged by the same merchant at regular intervals. The input is the grouped DataFrame, and the output is a list of suspected recurring charges.  
While highly valuable to the end user, this component is technically complex and must be explicitly deferred until after the Wednesday deadline. Calculating time deltas between rows grouped by merchant requires utilizing the pandas.Series.dt accessor to extract specific precision units8, days, and months9, and then applying complex shifting and differencing logic across the rows. This introduces severe complexity regarding edge cases, such as a user visiting the same coffee shop twice in one day for the exact same amount. Given the strict 2.5-day constraint, attempting to implement this will jeopardize the stability of the core ETL pipeline.

### **5.8. SQLite Storage and SQL Queries**

Local persistence allows the application to maintain a history of transactions across multiple executions without requiring the user to re-import CSV files continuously. The inputs are the final, enriched DataFrames, and the output is a populated local SQLite .db file. This is absolutely essential.  
SQLite is a C library providing a lightweight disk-based database that requires no separate server process or complex network configuration, making it perfectly suited for local Python applications1. Database interaction is managed via the standard sqlite3.connect() function1. The developer can utilize the pandas.DataFrame.to\_sql method to seamlessly migrate data from working memory directly to disk10. The primary implementation difficulty involves handling the if\_exists parameter. For the MVP, a simple if\_exists='replace' strategy is sufficient and robust. A major failure case is schema mismatch, which occurs if the DataFrame columns change between executions and the database attempts an append operation. Testing involves writing data to an in-memory SQLite database utilizing the sqlite3.connect(':memory:') string, and then using pandas.read\_sql11 to retrieve and verify the records, thereby avoiding the creation of leftover test files on the host machine.

### **5.9. Report Generation or Command-Line Output**

The user must be able to view the results of the analysis without querying the database directly. The input is the aggregated data and anomaly lists, and the output is a formatted string printed to the terminal. This is essential for the application to be demonstrable.  
The implementation difficulty is extremely low, relying on basic Python f-strings and terminal print statements. A common failure case is a poorly formatted output that is unreadable due to misaligned columns, missing line breaks, or excessive decimal places on floating-point numbers. Testing can be done visually by the developer during execution, or more formally by capturing standard output in the test suite, though visual validation is entirely acceptable for the Wednesday MVP constraint.

### **5.10. Optional Streamlit Dashboard**

Streamlit provides a fast path to web-based visual dashboards and interactive data applications12. However, this component must be strictly excluded from the Wednesday MVP. Streamlit fundamentally alters the execution model of the Python script, as the framework reruns the entire script from top to bottom upon every user interaction. Teaching a beginner the nuances of Streamlit's session state and caching mechanisms while they are simultaneously attempting to master Pandas and SQLite is a recipe for architectural collapse. The project must remain a standard command-line interface application for the MVP.

### **5.11. Automated Tests**

Automated tests ensure the system does not silently break during refactoring or when new categorization rules are added. The inputs are specific internal functions, and the outputs are passing or failing test signals. This is essential, but the scope must be heavily constrained to fit the schedule.  
The developer should use the standard library unittest framework, specifically creating isolated test cases by subclassing unittest.TestCase13. The core difficulty lies in the beginner learning how to isolate functions for testing. Major failure cases involve writing tests that rely on external, mutating files rather than synthetic, hardcoded data dictionaries. To manage time, the developer should only write unit tests for the categorization rules and the anomaly mathematics. Advanced testing techniques, such as utilizing unittest.mock to intercept system calls14, should be avoided. Mocking introduces a layer of abstraction that is entirely unnecessary if the internal functions are designed to be pure—meaning they take a DataFrame in and return a DataFrame out without triggering side effects.

### **5.12. GitHub Repository and README**

Source control and documentation are fundamental engineering practices required for any internship-level portfolio piece. This is essential. The difficulty is minimal, assuming basic Git knowledge. The primary failure case is omitting the requirements.txt file or providing unclear execution instructions, which renders the project useless to external reviewers or recruiters who attempt to run the code. The README must clearly explain the schema of the expected CSV and the exact terminal command required to execute the main script.

## **6\. Sample CSV Schema and Transaction Rules**

To ensure the ETL pipeline functions correctly, the application must assume a rigid data contract. External bank CSVs vary wildly; some institutions separate income and expenses into distinct columns, while others use a single column with positive and negative identifiers. To shield the beginner from writing complex conditional ingestion logic, the developer must provide a strict sample CSV schema that acts as the required input format.

### **Recommended CSV Schema Definition**

| Column Header | Data Type | Description |
| :---- | :---- | :---- |
| **Date** | String (ISO 8601\) | Represents the transaction date. Enforcing a "YYYY-MM-DD" format prevents ambiguous parsing errors across different locales. |
| **Description** | String | Contains the raw merchant information and transaction narrative. |
| **Amount** | Float | Represents the monetary value of the transaction. Must not contain currency symbols (e.g., '\$' or '€') to ensure mathematical operations succeed. |

### **Sign Convention and Handling Ambiguity**

The application must enforce a strict, single-column amount convention to simplify mathematical aggregations. The system will define expenses as negative numbers and income, refunds, or incoming transfers as positive numbers. This mathematical contract ensures that executing a sum function on the 'Amount' column across all transactions accurately calculates the net cash flow. If an external bank CSV utilizes positive numbers for expenses, the developer's README instructions must dictate that the user manually negates the column in a spreadsheet program before import, or the script must provide an explicit, documented flag to flip the signs during the ingestion phase.  
Regarding transaction duplication: the application must not automatically assume that transactions with identical dates, amounts, and descriptions are duplicates. In personal finance, it is common for a user to make two identical purchases at the same merchant on the same day (e.g., buying two separate coffees hours apart). A safe beginner-level import policy relies on run-level dataset replacement rather than granular row-level hashing, ensuring all legitimate transactions are captured.

### **Synthetic CSV Example**

The following dataset is explicitly labeled as synthetic data, constructed solely to represent the required data contract and test various edge cases in the ETL pipeline.

| Date | Description | Amount | Rationale for Inclusion |
| :---- | :---- | :---- | :---- |
| 2026-01-05 | WHOLEFOODS MKT 0192 | \-142.50 | Standard expense. Tests string normalization and basic rule matching logic. |
| 2026-01-06 | UBER \*TRIP | \-14.20 | Standard expense. Tests the handling of special characters (asterisks) in the merchant string. |
| 2026-01-15 | ACME CORP PAYROLL | 2500.00 | Positive income. Tests the sign convention and protects against false anomaly flagging for large income deposits. |
| 2026-01-18 | AMZN Prime Video | \-8.99 | Small recurring expense. Tests the lower bound of categorizations. |
| 2026-01-19 | BEST BUY \#992 | \-1850.00 | Large outlier expense. Explicitly designed to trigger the statistical standard-deviation anomaly detection logic. |
| 2026-01-20 |  | \-5.00 | Missing description. Tests the programmatic imputation of "UNKNOWN\_MERCHANT" and fallback categorization. |
| 2026-01-22 | REFUND SBUX STORE | 4.50 | Positive refund. Tests that refunds are mathematically treated as income rather than expenses. |

## **7\. Minimal Project-Folder Structure**

The repository must remain flat and highly accessible. Complex nested packages and highly abstract configuration files are unnecessary for a 2.5-day project and severely hinder code comprehension for beginners. The folder structure below enforces the Single Responsibility Principle without over-engineering the application.

| Directory / File | Single Responsibility |
| :---- | :---- |
| data/sample\_transactions.csv | Serves as the verified input file adhering perfectly to the data contract. |
| data/synthetic\_test\_data.csv | Provides controlled, hardcoded data exclusively for the automated test suite. |
| spendsense\_db.sqlite | Generated automatically at runtime by the SQLite library; must be ignored via .gitignore to prevent committing personal data. |
| main.py | Acts as the sole entry point. Handles basic command-line execution, configures logging, and orchestrates the sequence of function calls. |
| pipeline.py | Contains the pure data transformation functions, including cleaning, normalization, and the mathematical anomaly logic. |
| rules.py | A dedicated configuration file housing the Python dictionary used for categorizing normalized merchant strings. |
| storage.py | Encapsulates all database operations, managing the SQLite connection and executing the Pandas to\_sql and read\_sql methods. |
| tests/test\_pipeline.py | Contains the unittest.TestCase classes validating the cleaning and anomaly mathematical logic. |
| tests/test\_rules.py | Contains the unittest.TestCase classes validating that known merchant strings map to their expected categories. |
| requirements.txt | An explicit, pip-installable list of external dependencies (e.g., Pandas). |
| README.md | Documents the project goal, local setup instructions, data schema rules, and exact terminal execution commands. |

## **8\. Essential Dependencies and Verified Installation Guidance**

The architecture relies heavily on the Python Standard Library to limit the installation footprint, reduce security vulnerabilities, and minimize deployment friction. Modules such as sqlite3 for databases, pathlib for file routing, logging for error handling, and unittest for quality assurance are built directly into the Python interpreter and require no external downloading.  
The only required third-party dependency for this architecture is Pandas. Pandas is thoroughly justified because it vastly simplifies the manipulation of tabular data, provides vectorized string operations that are exponentially faster and cleaner than iterative Python for loops, and includes native SQL translation methods that abstract away complex insert statements.  
To ensure stability and reproducibility, the dependency must be explicitly tracked. A virtual environment is highly recommended to isolate the project dependencies from the developer's system-level Python packages, preventing version conflicts.  
The verified installation workflow requires the developer to open a terminal and execute the following commands to establish the environment and install the required library:

> 1. python \-m venv venv (Initializes the virtual environment)  
> 2. source venv/bin/activate (Activates the environment on Unix/macOS; Windows users must utilize venv\\Scripts\\activate)  
> 3. pip install pandas==2.2.0 (Installs a specific, stable version of Pandas to guarantee consistent behavior)

## **9\. Main Implementation Risks**

Even within a highly constrained MVP, a beginner faces several systemic implementation risks that must be proactively mitigated through careful architectural choices.  
Firstly, file path resolution is a frequent source of error. Hardcoding absolute file paths (e.g., C:/Users/Name/Desktop/data.csv) guarantees the script will fail when evaluated by a recruiter, instructor, or peer reviewer on a different machine. The developer must utilize the standard library pathlib module, which offers object-oriented filesystem paths15. By constructing relative paths using pathlib.Path(\_\_file\_\_).parent, the application dynamically resolves the correct directory regardless of the host operating system, rendering the older os.path string manipulations unnecessary16.  
Secondly, silent failures on corrupted data pose a significant risk. If a user provides a CSV with a trailing comma creating a phantom column on line 42, the entire ingestion script might crash abruptly. The developer must leverage the robust parsing arguments within Pandas. Specifically, setting on\_bad\_lines='skip' or 'warn' within the read\_csv function call instructs the parser to discard the corrupted line and continue processing the rest of the file2, ensuring the application remains resilient.  
Thirdly, unhandled exceptions provide a poor user experience. Relying on raw print() statements makes debugging difficult. The developer must implement the standard logging module, utilizing logging.basicConfig to establish a uniform format for warnings and informational messages17. This professionalizes the terminal output and assists in tracing ingestion errors.  
Finally, while the risk of malicious SQL injection is negligible in a local, single-user personal finance application, poorly formatted merchant strings containing unescaped quotation marks can break raw SQL insert statements. Utilizing the Pandas to\_sql method entirely bypasses this risk, as SQLAlchemy (which underpins the Pandas SQL engine) parameterizes the inputs safely under the hood, ensuring data integrity10.

## **10\. Essential Test Cases**

To demonstrate professional software engineering practices without overwhelming the 2.5-day schedule, testing must focus solely on logic that operates independently of the file system and external databases. The unittest framework should be utilized to execute the following core scenarios.  
The developer must construct a test class subclassing unittest.TestCase13 to perform Rule Matching Verification. This test passes a synthetic Pandas Series of known merchant names into the categorization function. The developer utilizes assertions to verify that the string "UBER EATS" maps precisely to "Dining", "SHELL OIL" maps to "Transport", and "MYSTERY STORE" maps safely to the fallback "Uncategorized" label.  
A second test case must validate the Anomaly Threshold Mathematics. The developer instantiates a mock DataFrame containing 99 transactions of \$10 and a single outlier transaction of \$10,000. This DataFrame is passed into the anomaly detection function. The test asserts that the function isolates only the \$10,000 transaction, confirming that the length of the returned anomaly DataFrame is exactly 1\.  
A third test case must verify Missing Value Imputation. A DataFrame containing null values in the 'Description' column is passed into the cleaning function. The test asserts that the resulting DataFrame has successfully replaced the null entities with the designated fallback string (e.g., "UNKNOWN\_MERCHANT"), preventing downstream string matching functions from throwing type errors.  
By testing pure functions that accept DataFrames as arguments and return modified DataFrames, the developer completely circumvents the complexity of mocking file system handlers or database connections, maintaining a fast, reliable test suite.

## **11\. Features to Exclude Until After Wednesday**

To fiercely protect the Wednesday deadline, the developer must strictly avoid implementing the following components, regardless of how impressive they might appear on a resume or portfolio. Including these features guarantees the project will not reach a demonstrable state within 2.5 days.  
Machine learning models, such as training isolation forests for anomaly detection or utilizing natural language processing (NLP) clustering algorithms for categorization, must be excluded. These approaches require massive training datasets to function accurately, introduce significant computational overhead, and blatantly violate the constraint that the logic must be highly explainable by a beginner in an interview setting.  
Streamlit or alternative web dashboards must be excluded. User interface frameworks require reactive state management, asynchronous event loops, and complex layout logic. This distracts entirely from the core objective of mastering backend data engineering, Pandas transformations, and SQL querying.  
External API integrations, such as connecting to Plaid or other financial data aggregators, must be excluded. Establishing these connections requires handling secret API keys, managing OAuth token flows, and dealing with unpredictable network latency. This is vastly beyond the scope of a 2.5-day MVP and introduces security risks regarding personal financial credentials.  
Cloud databases and hosting must be excluded. Configuring PostgreSQL on Amazon Web Services (AWS) or deploying to platforms like Supabase adds severe network dependencies, firewall configurations, and credential management overhead. The local SQLite database is explicitly mandated and completely sufficient for the project goals.  
Advanced SQLite configurations, such as implementing Write-Ahead Logging (WAL) or concurrency tuning, must be excluded. While these features are critical for high-traffic web applications1, they are entirely irrelevant for a single-user, single-threaded analytical script running locally.

## **12\. A Realistic 2.5-Day Implementation Schedule**

To ensure successful delivery by Wednesday, the developer must adhere to a strict timeboxed schedule, treating the available time as roughly 20 hours of focused engineering.  
**Day 1: Ingestion, Validation, and Core Logic**  
The morning block focuses on establishing the environment. The developer initializes the Git repository, configures the virtual environment, installs Pandas, and creates the data/ folder, populating it with the synthetic CSV. The afternoon block transitions to writing the ingestion logic in pipeline.py. The developer ensures dates parse correctly and amounts are converted to floats, followed by implementing the string normalization function. The evening block is dedicated to writing the rule dictionary in rules.py and applying it to the DataFrame to generate categories, verifying the output visually via terminal print statements.  
**Day 2: Analysis, Persistence, and Testing** The morning block focuses on mathematics. The developer implements the statistical anomaly detection function and writes the grouping logic to sum expenses by category. The afternoon block introduces persistence. The developer implements SQLite storage in storage.py, establishing the database connection1 and successfully executing the to\_sql method to save the categorized data to the local disk10. The evening block is dedicated to quality assurance. The developer writes the unittest cases for the categorization and anomaly math, ensuring all assertions pass. The logging module is also connected to output progress and errors cleanly.  
**Day 3: Reporting and Final Polish**  
The final morning focuses on orchestration and presentation. The developer finalizes main.py to link the functions together in a seamless pipeline. The terminal output is formatted using Python f-strings to align text and improve readability. The final hours are spent writing the README.md, executing the script from a fresh terminal instance to verify end-to-end functionality, and pushing the finalized code to the GitHub repository.

## **13\. Verified Source Register**

The architectural recommendations and implementation strategies detailed in this report are grounded in the verified capabilities of the proposed technology stack, referencing official documentation to ensure accuracy.  
The SQLite database mechanics rely on the standard library's sqlite3 module, which provides a C-library-based, lightweight disk database that operates without a separate server process. This makes it the definitive choice for local persistence1. The required database connections are established natively via the sqlite3.connect() function1.  
Pandas CSV ingestion strategies are based on the robust pandas.read\_csv function, which handles unstructured text ingestion. The documentation verifies that the on\_bad\_lines parameter safely processes corrupted datasets by skipping or warning about irregular rows2.  
Pandas SQL integration relies on the DataFrame.to\_sql method, which bridges the gap between memory and persistent storage, allowing seamless exportation of cleaned data directly into the SQLite schema10. Verification of data retrieval is supported by the pandas.read\_sql method11.  
String manipulation and categorization logic rely on the Series.str.contains method6 and general vectorized string functions5, which the documentation confirms are heavily optimized compared to standard Python iterative loops. Datetime processing relies on the dt accessor to extract high-level representations such as years and months9.  
Operating-system-agnostic file path resolution is supported by the pathlib module15, which supersedes the older string-based os.path module16.  
Testing infrastructure is verified against the built-in unittest.TestCase class13, while explicitly avoiding the unittest.mock library to maintain simplicity14. Professional system logging is supported by the logging.basicConfig function17.

## **14\. Unresolved Questions and Final Pre-Coding Checklist**

Before writing the first line of code, the developer must finalize decisions on the following minor operational details to ensure the pipeline is constructed without hesitation:  
Firstly, the exact threshold for anomalies must be finalized. The developer must decide whether the anomaly threshold will be a hardcoded standard deviation multiplier (e.g., greater than 2.5 times the standard deviation) or a simpler static dollar amount (e.g., greater than \$500). The standard deviation approach is highly recommended as it scales dynamically with the user's specific income level, but a static threshold serves as a viable fallback if the implementation proves challenging.  
Secondly, the fallback categorization naming convention must be established. The developer must decide the exact string that will represent unmatched merchants. Options include "Uncategorized", "Other", or "Review Required". Absolute consistency here is vital, as the downstream grouping and aggregation logic depends on uniform labels.  
Finally, the handling of command-line arguments must be decided. The developer must choose whether main.py will accept the CSV file path dynamically via an argument using the sys or argparse modules, or whether it will simply look for a hardcoded default file name in the data/ directory. Utilizing argparse adds a layer of professionalism but introduces slight complexity; a hardcoded default path via pathlib is safer for the MVP if time is critically short.

#### **Works cited**

> 1. sqlite3 — DB-API 2.0 interface for SQLite databases — Python 3.15, [https\://docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)  
> 2. pandas.read\_csv — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.read\_csv.html](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)  
> 3. csv — CSV file reading and writing — Python 3.15.0 documentation, [https\://docs.python.org/3/library/csv.html](https://docs.python.org/3/library/csv.html)  
> 4. pandas.to\_datetime — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.to\_datetime.html](https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html)  
> 5. pandas.Series.str — pandas 3.0.6 documentation, [https\://pandas.pydata.org/docs/reference/api/pandas.Series.str.html](https://pandas.pydata.org/docs/reference/api/pandas.Series.str.html)  
> 6. pandas.Series.str.contains — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.Series.str.contains.html](https://pandas.pydata.org/docs/reference/api/pandas.Series.str.contains.html)  
> 7. pandas.DataFrame.groupby — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html)  
> 8. pandas 3.0.5 documentation \- Series.dt.unit \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.Series.dt.unit.html](https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.unit.html)  
> 9. pandas.Series.dt.month — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.Series.dt.month.html](https://pandas.pydata.org/docs/reference/api/pandas.Series.dt.month.html)  
> 10. pandas.DataFrame.to\_sql — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to\_sql.html](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html)  
> 11. pandas.read\_sql — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read\_sql.html](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_sql.html)  
> 12. Input widgets \- Streamlit Docs, [https\://docs.streamlit.io/develop/api-reference/widgets](https://docs.streamlit.io/develop/api-reference/widgets)  
> 13. unittest — Unit testing framework — Python 3.15.0 documentation, [https\://docs.python.org/3/library/unittest.html](https://docs.python.org/3/library/unittest.html)  
> 14. unittest.mock — mock object library — Python 3.15.0 documentation, [https\://docs.python.org/3/library/unittest.mock.html](https://docs.python.org/3/library/unittest.mock.html)  
> 15. pathlib — Object-oriented filesystem paths — Python 3.15.0, [https\://docs.python.org/3/library/pathlib.html](https://docs.python.org/3/library/pathlib.html)  
> 16. os.path — Common pathname manipulations — Python 3.15.0, [https\://docs.python.org/3/library/os.path.html](https://docs.python.org/3/library/os.path.html)  
> 17. logging — Logging facility for Python — Python 3.15.0 documentation, [https\://docs.python.org/3/library/logging.html](https://docs.python.org/3/library/logging.html)  
> 18. Logging HOWTO — Python 3.15.0 documentation, [https\://docs.python.org/3/howto/logging.html](https://docs.python.org/3/howto/logging.html)  
> 19. pandas.read\_sql\_query — pandas 3.0.6 documentation \- PyData |, [https\://pandas.pydata.org/docs/reference/api/pandas.read\_sql\_query.html](https://pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html)  
> 20. pandas.Series.dt — pandas 3.2.0.dev0 documentation \- PyData |, [https\://pandas.pydata.org/docs/dev/reference/api/pandas.Series.dt.html](https://pandas.pydata.org/docs/dev/reference/api/pandas.Series.dt.html)