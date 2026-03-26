\documentclass[a4paper,10pt]{article}

% Packages
\usepackage[a4paper, top=0.6in, bottom=0.6in, left=0.65in, right=0.65in]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{parskip}
\usepackage{fontenc}
\usepackage{inputenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{array}
\usepackage{tabularx}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{wasysym}
\usepackage{marvosym}
\usepackage{amssymb}

% Colors
\definecolor{sectiongray}{RGB}{230,230,230}

% Hyperlink setup
\hypersetup{
    colorlinks=false,
    pdfborder={0 0 0}
}

% Section formatting
\titleformat{\section}
  {\normalfont\normalsize\bfseries}
  {}
  {0pt}
  {}
  [{\vspace{1pt}\color{black}\titlerule[0.4pt]\vspace{2pt}}]

\titlespacing*{\section}{0pt}{8pt}{4pt}

% Custom section with gray background
\newcommand{\resumesection}[1]{%
  \vspace{4pt}%
  \noindent\colorbox{sectiongray}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{\textbf{#1}}}%
  \vspace{3pt}%
}

% List settings
\setlist[itemize]{leftmargin=1.5em, itemsep=1pt, topsep=2pt, parsep=0pt}

% No paragraph indent
\setlength{\parindent}{0pt}
\setlength{\parskip}{2pt}

\pagestyle{empty}

\begin{document}

% ─── HEADER ───────────────────────────────────────────────────────────────────
\begin{center}
    {\LARGE\textbf{RAHUL GIRI}}\\[3pt]
    {\large\textbf{SOFTWARE ENGINEER}}\\[5pt]
    \Letter\ \href{mailto:sparamanik1221@gmail.com}{girirahul7001@gmail.com}
    \quad \textbullet \quad
    \Mobilefone\ 8250645880
    \quad \textbullet \quad
    $\bullet$\ Bengaluru, Karnataka
\end{center}

\vspace{2pt}

% ─── PROFILE SUMMARY ──────────────────────────────────────────────────────────
\resumesection{PROFILE SUMMERY}

\begin{itemize}[label=\tiny$\blacksquare$]
    \item Total 3.4 years of experience as a Software Engineer specializing in web application development
    \item using \textbf{Python, Django, Flask,} and \textbf{Fast API.}\\
    Proficient in cloud technologies like \textbf{AWS (EC2, S3, Lambda, Cloud Watch)} and experienced in
    \item[\tiny$\blacksquare$] deploying applications using \textbf{Docker} and \textbf{Kubernetes.}
    \item Hands-on experience with database management with \textbf{MySQL, PostgreSQL.}\\
    Skilled in developing scalable and secure back-end solutions with a focus on API development, security compliance, and data protection protocols.
    \item Expertise in CI/CD pipelines using tools like \textbf{Jenkins} and \textbf{GitHub}, ensuring seamless development and deployment cycles.
    \item Adept at API testing using \textbf{Postman} and \textbf{Swagger}, with strong version control experience using \textbf{Git} and \textbf{Bitbucket}.
    \item \textbf{Agile Scrum} methodology experience with strong collaboration skills in cross-functional teams and active participation in daily \textbf{standups, sprint planning,} and \textbf{code reviews.}
    \item Passionate about leveraging analytical and problem-solving skills to create innovative software solutions while continuously developing both technical and interpersonal skills.
\end{itemize}

\vspace{2pt}

% ─── TECHNICAL SKILLS ─────────────────────────────────────────────────────────
\resumesection{TECHNICAL SKILLS}

\vspace{4pt}
\begin{tabular}{@{} p{0.48\linewidth} p{0.48\linewidth} @{}}
    \textbf{Programming Languages} & \textbf{Libraries/Frameworks} \\
    Python & NumPy, Pandas, Django, Flask, FastAPI \\[4pt]
    \textbf{Database} & \textbf{Cloud Technologies} \\
    MySQL, PostgreSQL & AWS - EC2, S3, Lambda, Cloud Watch \\[4pt]
    \textbf{API Testing} & \textbf{Version Control} \\
    Postman, Swagger & GitHub, Bitbucket \\[4pt]
    \textbf{Methodologies} & \textbf{Others} \\
    Agile, Scrum & Kafka, Docker, Confluence, Bamboo, Jira, \\[4pt]
    \textbf{Frontend} & Git \\
    HTML, Css, Javascripts & \\
\end{tabular}

\vspace{2pt}

% ─── WORK EXPERIENCE ──────────────────────────────────────────────────────────
\resumesection{WORK EXPERIENCE}

\begin{itemize}[label=\tiny$\blacksquare$]
    \item Currently working as Software Engineer at Fortmindz Private Limited from JAN - 2025 to till date.
\end{itemize}

\vspace{2pt}

% ─── PROFESSIONAL EXPERIENCE ──────────────────────────────────────────────────
\resumesection{PROFESSIONAL EXPERIENCE}

\vspace{4pt}
\noindent\textbf{Project 2: Timesheet application} \hfill \textbf{August 2024 -- Till Date}\\
\textbf{Designation:} Software Engineer\\
\textbf{Client:} Exxonmobil\\
\textbf{Technologies:} Python, FastAPI, REST APIs, SQLAlchemy, Docker, Kubernetes, AWS

\vspace{4pt}
\textbf{Description}:

\noindent Developed an enterprise-level timesheet and workflow management system for a global client using Python, FastAPI, REST APIs, and SQLAlchemy. The application manages timesheet groups, payroll applicability using effective date logic, approval workflows, and bulk data processing, and is deployed on Docker, Kubernetes, and AWS to ensure scalability, reliability, and data integrity.

\vspace{3pt}
\textbf{Roles \& Responsibilities:}
\begin{itemize}[label=\tiny$\blacksquare$]
    \item Developed \textbf{RESTful APIs} using \textbf{FastAPI} and \textbf{Python} for timesheet group and workflow management.
    \item Implemented \textbf{effective date} (month/year) logic to control timesheet group applicability across payroll periods.
    \item \textbf{Built bulk CSV upload} functionality with validation, error handling, and transactional consistency.
    \item Designed and maintained relational database schemas using \textbf{SQLAlchemy} with proper constraints and indexing.
    \item Implemented \textbf{employee--business unit workflow} mapping with approval hierarchy.
    \item Developed \textbf{APIs for create, update, delete,} and \textbf{retrieve} timesheet groups.
    \item Ensured \textbf{data integrity} and consistency during updates and bulk operations.
    \item Containerized the application using \textbf{Docker} and supported deployment on \textbf{Kubernetes}.
    \item Collaborated with \textbf{stakeholders} to understand requirements and align the solution with enterprise standards.
\end{itemize}

\vspace{6pt}
\noindent\textbf{Project 1:  Grievance Portal } \hfill \textbf{Dec 2023 -- Sept 2024}\\
\textbf{Designation:} Junior Software Engineer\\
\textbf{Client:} Govt Of West Bengal\\
\textbf{Technologies:} Python, Django, PostgreSQL,Redis, RabbitMQ, Celery, AWS S3,Jenikins Linux(RHEL), Docker, Unit Test, mock, Agile, Scrum

\vspace{4pt}
\textbf{Description}:

\noindent Grievance Portal is a centralized digital governance platform developed for the Got of West Bengal, enabling citizens to seamlessly register, track, and resolve complaints against public departments and services. The platform facilitates grievance submission through three distinct channels Self , CMO Helpline, and PGMS System ensuring accessibility for a diverse citizen base. It supports multilingual complaint filling along with document attachments, automated department-wise routing, and district-level nodal officer assignment to enforce accountability and drive timely resolution across the state administration.

\vspace{3pt}
\textbf{Roles \& Responsibilities:}
\begin{itemize}[label=\tiny$\blacksquare$]
    \item Developed and maintained backend features for a multi-tenant Grievance Portal platform using \textbf{Python} and \textbf{Django}.
    \item Implemented \textbf{role-based access control (RBAC)}, secure user authentication, and data protection protocols for citizens, nodal officers, and administrators.
    \item Designed and built \textbf{database models, REST APIs,} and server-side views to support scalable, interactive web applications.
    \item Perfomance Tunning and optimized \textbf{PostgreSQL} database schemas to manage citizen grievance records, department mappings, and resolution workflows efficiently..
    \item Wrote \textbf{unit tests} and \textbf{mock tes}t cases to ensure code quality, reliability, and maintainability.
    \item Supported Grievance architecture enhancements, enabling organization-level service management and usage tracking.
    \item Collaborated in Agile/Scrum ceremonies, including sprint planning, reviews, and daily standups.
\end{itemize}

\vspace{2pt}

% ─── EDUCATION ────────────────────────────────────────────────────────────────
\resumesection{EDUCATION}

\vspace{4pt}
\noindent\textbf{M.Tech - Computer Science and Engineering} \hfill \textbf{2020 - 2022}\\
Maulana Abul Kalam Azad University of Technology, West Bengal

\vspace{4pt}
\noindent\textbf{B.Tech - Computer Science and Engineering} \hfill \textbf{2016 - 2020}\\
Bankura Unnayani Institute of Engineering, West Bengal

\vspace{2pt}

% ─── DECLARATION ──────────────────────────────────────────────────────────────
\resumesection{DECLARATION}

\vspace{4pt}
\noindent I hereby declare that the information provided in this resume is true and correct to the best of my knowledge and belief.

\vspace{10pt}
\hfill\textbf{Rahul Giri}

\end{document}