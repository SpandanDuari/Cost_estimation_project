# Software Cost Estimation Tool - Spring Boot Version

## Project Overview
Build a Java Spring Boot web application that calculates software development costs using the COCOMO model. Port of existing Python/Flask project without AI component.

**Tech Stack:** Java 11+, Spring Boot 3.x, Spring Security, JPA/Hibernate, Thymeleaf, SQLite, iText (PDF), Maven

---

## Database Schema

### Users Table
```
id (INT, PK, Auto-increment)
username (VARCHAR(255), UNIQUE, NOT NULL)
password_hash (TEXT, NOT NULL)
is_admin (INT, NOT NULL, DEFAULT 0)
created_at (DATETIME, NOT NULL)
```

### Reports Table
```
id (INT, PK, Auto-increment)
user_id (INT, FK → users.id, NOT NULL)
created_at (DATETIME, NOT NULL)
effort (DOUBLE, NOT NULL)          // Person-Months
time (DOUBLE, NOT NULL)            // Months
cost (DOUBLE, NOT NULL)            // Total Cost in INR
```

---

## Core Features

### 1. User Management
- **Signup:** Create account with username/password
- **Login:** Session-based authentication
- **Logout:** Clear session
- **Delete Account:** Admin-only (cannot delete own or other admins)
- **Default Admin:** Auto-create on first startup (admin/admin123)
- **Roles:** Regular User vs Admin

### 2. Cost Estimation Engine
**Inputs:** Lines of Code (LOC) and Cost per Developer (must be > 0)

**COCOMO Organic Mode Calculation:**
```
KLOC = LOC / 1000
Effort = 2.4 * (KLOC ^ 1.05)       // Person-Months
Time = 2.5 * (Effort ^ 0.38)       // Months
Total Cost = Effort * Cost per Developer
```

**Output:** Effort, Development Time, Total Cost (rounded to 2 decimals)

### 3. Report Management
- Save estimation results with user_id and timestamp
- Users view only own reports; admins view all
- Users delete only own; admins delete any
- Report detail page with full metadata

### 4. Report Export
- **Download as TXT:** Plaintext format
- **Download as PDF:** Formatted document (iText)
- Users can download own; admins can download any

### 5. Admin Dashboard
- View all users with creation dates
- View all reports across users
- Delete user accounts with confirmation

### 6. Security
- BCryptPasswordEncoder for passwords
- Session-based authorization
- Per-resource access checks (users cannot access others' reports)
- Admin-only routes protected
- CSRF protection (default)

---

## Routes/Endpoints

### Public
- `GET /` → Redirect to dashboard or login
- `GET /auth`, `POST /auth` → Login
- `GET /signup`, `POST /signup` → Register

### Protected (login required)
- `GET /dashboard` → Estimation form + report history
- `POST /dashboard` → Submit estimation
- `GET /download` → Report download page
- `GET /report/<id>` → Report detail
- `POST /delete-report/<id>` → Delete report
- `GET /download-report/<id>` → Download TXT
- `GET /download-report-pdf/<id>` → Download PDF
- `GET /logout` → Logout

### Admin-only
- `POST /admin/delete-user/<id>` → Delete user

---

## Entities & Repositories

### User Entity
```java
@Entity @Table(name = "users")
class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;
    
    @Column(unique = true, nullable = false)
    String username;
    
    @Column(nullable = false)
    String passwordHash;
    
    @Column(name = "is_admin", nullable = false)
    Integer isAdmin;  // 0 or 1
    
    LocalDateTime createdAt;
    
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL)
    List<Report> reports;
}
```

### Report Entity
```java
@Entity @Table(name = "reports")
class Report {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    User user;
    
    LocalDateTime createdAt;
    Double effort;   // Person-Months
    Double time;     // Months
    Double cost;     // INR
}
```

### Repositories
```
UserRepository extends JpaRepository<User, Long>
  - findByUsername(String username)

ReportRepository extends JpaRepository<Report, Long>
  - findByUserId(Long userId)
  - findAllByOrderByIdDesc()
```

---

## Services

### UserService
- registerUser(username, password)
- authenticateUser(username, password)
- getUserByUsername(username)
- getAllUsers()
- deleteUser(userId, currentUserId, currentUserIsAdmin)
- initializeDefaultAdmin() [run on startup]

### ReportService
- createReport(userId, effort, time, cost)
- getReportsByUser(userId)
- getAllReports()
- getReportById(reportId)
- deleteReport(reportId, userId, isAdmin)
- validateEstimationInput(loc, costPerDev)

### EstimationService
- calculateCOCOMO(loc, costPerDev) → return Map<String, Double> with effort/time/cost

### PDFGenerationService
- generateReportPDF(report, username) → ByteArrayOutputStream

---

## Controllers

### AuthController
- GET/POST /auth (login)
- GET/POST /signup (register)
- GET /logout

### DashboardController
- GET /dashboard
- POST /dashboard (with validation & COCOMO calculation)

### ReportController
- GET /download
- GET /report/<id>
- POST /delete-report/<id>
- GET /download-report/<id> (TXT)
- GET /download-report-pdf/<id> (PDF)

### AdminController
- POST /admin/delete-user/<id>

---

## Templates (Thymeleaf)

- **login.html** — Username/password form, link to signup
- **signup.html** — Registration form, success/error messages
- **index.html** (dashboard) — Estimation form, result display, report history table, admin user table
- **download.html** — List of reports with TXT/PDF download links
- **report_detail.html** — Full report metadata, delete/download buttons

---

## Configuration (application.properties)

```properties
spring.application.name=cost-estimation
server.port=8080

# SQLite Database
spring.datasource.url=jdbc:sqlite:cost_estimation.db
spring.datasource.driver-class-name=org.sqlite.JDBC
spring.jpa.database-platform=org.hibernate.dialect.SQLiteDialect
spring.jpa.hibernate.ddl-auto=create-if-not-exists

# Thymeleaf
spring.thymeleaf.cache=false

# Session
server.servlet.session.timeout=30m

# Logging
logging.level.root=INFO
logging.level.com.cost.estimation=DEBUG
```

---

## Maven Dependencies (pom.xml)

```xml
<!-- Spring Boot Web -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- Spring Data JPA -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>

<!-- Spring Security -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>

<!-- Thymeleaf -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-thymeleaf</artifactId>
</dependency>

<!-- Validation -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>

<!-- SQLite JDBC -->
<dependency>
    <groupId>org.xerial</groupId>
    <artifactId>sqlite-jdbc</artifactId>
    <version>3.43.0.0</version>
</dependency>

<!-- iText PDF -->
<dependency>
    <groupId>com.itextpdf</groupId>
    <artifactId>itextpdf</artifactId>
    <version>5.5.13.2</version>
</dependency>

<!-- Lombok (optional) -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>

<!-- Spring Boot Test -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

---

## Project Structure

```
cost-estimation-springboot/
├── src/main/java/com/cost/estimation/
│   ├── CostEstimationApplication.java
│   ├── config/
│   │   ├── SecurityConfig.java
│   ├── controller/
│   │   ├── AuthController.java
│   │   ├── DashboardController.java
│   │   ├── ReportController.java
│   │   ├── AdminController.java
│   ├── entity/
│   │   ├── User.java
│   │   ├── Report.java
│   ├── repository/
│   │   ├── UserRepository.java
│   │   ├── ReportRepository.java
│   ├── service/
│   │   ├── UserService.java
│   │   ├── ReportService.java
│   │   ├── EstimationService.java
│   │   ├── PDFGenerationService.java
│   ├── dto/
│   │   ├── EstimationRequest.java
│   │   ├── EstimationResult.java
│
├── src/main/resources/
│   ├── application.properties
│   ├── templates/
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── index.html
│   │   ├── download.html
│   │   ├── report_detail.html
│   ├── static/
│   │   ├── style.css (optional)
│
├── pom.xml
└── README.md
```

---

## Key Implementation Notes

✅ **Input Validation** — All numeric inputs must be > 0 before database save  
✅ **Authorization** — Always verify ownership or admin status before access  
✅ **Error Handling** — Return meaningful error messages to UI  
✅ **Password Security** — Use BCryptPasswordEncoder, never store plaintext  
✅ **Session Management** — Spring Security handles automatically  
✅ **PDF Generation** — Use iText to draw text on canvas  
✅ **Testing** — Write unit tests for services, integration tests for controllers  

---

## Run Instructions

```bash
# Build
mvn clean install

# Run
mvn spring-boot:run

# Access
http://localhost:8080/auth

# Default Login
Username: admin
Password: admin123
```

---

## Deliverables

✅ Fully functional Spring Boot web app  
✅ User authentication & role-based access  
✅ COCOMO estimation calculations  
✅ Report CRUD operations  
✅ TXT & PDF exports  
✅ Admin dashboard  
✅ SQLite database  
✅ Thymeleaf templates  
✅ Error handling & validation  
✅ README with setup instructions
