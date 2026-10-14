from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from bcm_app.models import (
    CriticalService, ICTThirdParty, ServiceDependency,
    BusinessImpactAnalysis, BCPlan, BCPEmergencyContact,
    Scenario, RTEPTestExercise, Finding, EvidenceItem,
    ApprovalTask, AuditLogEntry, Notification, ResQChatLog
)

class Command(BaseCommand):
    help = "Seed realistic enterprise BCM data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding BCM data...")

        # 1. ICT Third Parties
        vendors_data = [
            ("VEND-AWS-01", "Amazon Web Services", "Cloud Infrastructure (Compute, S3, Aurora DB)", "Critical", "support-ent@aws.amazon.com", 99.99, "AWS eu-central-1 (Frankfurt)"),
            ("VEND-EQUINIX-02", "Equinix Data Centers", "Tier IV On-Premises Colocation & Cross-Connects", "Critical", "noc@equinix.com", 99.999, "Frankfurt FR5 / Zurich ZH2"),
            ("VEND-SWIFT-03", "SWIFT SC", "Global Financial Messaging Network", "Critical", "security-desk@swift.com", 99.98, "SWIFT Secured Network"),
            ("VEND-CARD-04", "Mastercard / Visa Rails", "Payment Card Authorization Network", "Critical", "enterprise-ops@mastercard.com", 99.99, "Global Private Network"),
            ("VEND-CLF-05", "Cloudflare Enterprise", "DDoS Mitigation, WAF & Global Anycast DNS", "High", "soc@cloudflare.com", 99.999, "Global Anycast Edge"),
            ("VEND-REFINITIV-06", "Refinitiv / LSEG", "Market Data Feeds & Real-Time FX Rates", "Medium", "support@lseg.com", 99.90, "London / Frankfurt"),
        ]

        vendors = {}
        for code, name, svc, crit, email, sla, region in vendors_data:
            v, _ = ICTThirdParty.objects.get_or_create(
                vendor_code=code,
                defaults={
                    "name": name,
                    "service_provided": svc,
                    "criticality": crit,
                    "contact_email": email,
                    "sla_percentage": sla,
                    "hosting_region": region,
                    "status": "Active",
                    "dora_compliant": True
                }
            )
            vendors[code] = v

        # 2. Critical Services
        services_data = [
            ("SVC-PAY-01", "Real-Time Payment Engine (SEPA / Faster Payments)", "Instant payment rails processing consumer and corporate instant fund transfers.", "Tier 1", "Dr. Sarah Jenkins", "Payments & Settlement", 1.0, 0.0, 2.0, 150000.00),
            ("SVC-SWIFT-02", "SWIFT Cross-Border Clearing", "Interbank correspondent clearing and international wires messaging engine.", "Tier 1", "Marcus Vance", "Treasury & Global Markets", 2.0, 0.5, 4.0, 280000.00),
            ("SVC-CORE-03", "Core Banking Account Ledger", "High-frequency central transactional book of records and interest engine.", "Tier 1", "Elena Rostova", "Core Technology", 1.5, 0.25, 3.5, 220000.00),
            ("SVC-CARD-04", "Card Issuing & ATM Switch", "Real-time debit/credit card authorization, POS switch, and ATM telemetry.", "Tier 1", "David Chen", "Retail Banking Cards", 1.0, 0.2, 2.5, 175000.00),
            ("SVC-MBANK-05", "Digital Banking Mobile & Web App", "Customer-facing omni-channel web portal and native iOS/Android gateway.", "Tier 2", "Sophie Moreau", "Digital Channels", 3.0, 1.0, 6.0, 65000.00),
            ("SVC-AML-06", "AML & Real-time Sanctions Screener", "Sanctions matching and financial crime fraud detection during transaction flows.", "Tier 2", "Tariq Al-Mansoor", "Financial Crime Compliance", 4.0, 1.0, 8.0, 80000.00),
            ("SVC-FX-07", "FX & Treasury Electronic Trading", "Institutional spot FX, liquidity pooling, and derivative order management.", "Tier 1", "Julian Blake", "Capital Markets", 1.0, 0.1, 2.0, 310000.00),
            ("SVC-CRM-08", "Customer Operations & Contact Center", "Helpdesk telephony, CRM ticket resolution, and identity verification.", "Tier 3", "Rachel Adams", "Customer Experience", 8.0, 4.0, 24.0, 18000.00),
        ]

        services = {}
        for code, name, desc, tier, owner, dept, rto, rpo, mtpd, loss in services_data:
            s, _ = CriticalService.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "tier": tier,
                    "owner_name": owner,
                    "department": dept,
                    "rto_hours": rto,
                    "rpo_hours": rpo,
                    "mtpd_hours": mtpd,
                    "financial_loss_per_hour": loss,
                    "status": "Active",
                    "last_bia_date": date.today() - timedelta(days=45)
                }
            )
            services[code] = s

        # 3. Dependencies
        dependencies_data = [
            # Payment Engine depends on Core Ledger, AWS, and Cloudflare
            (services["SVC-PAY-01"], services["SVC-CORE-03"], None, "Internal Service", "Critical", 1, "Direct synchronous balance check & debit"),
            (services["SVC-PAY-01"], None, vendors["VEND-AWS-01"], "ICT Third Party", "Critical", 2, "Payment orchestration containers on AWS EKS"),
            (services["SVC-PAY-01"], None, vendors["VEND-CLF-05"], "ICT Third Party", "High", 3, "API ingress protection and TLS termination"),

            # SWIFT depends on Core Ledger and SWIFT network
            (services["SVC-SWIFT-02"], services["SVC-CORE-03"], None, "Internal Service", "Critical", 1, "Settlement posting against nostro accounts"),
            (services["SVC-SWIFT-02"], None, vendors["VEND-SWIFT-03"], "ICT Third Party", "Critical", 2, "Hardware security module (HSM) and SAG gateway"),
            (services["SVC-SWIFT-02"], None, vendors["VEND-EQUINIX-02"], "Facility / Data Center", "Critical", 3, "Equinix FR5 secure cage connection"),

            # Card Switch depends on Core Ledger, Mastercard, and Equinix
            (services["SVC-CARD-04"], services["SVC-CORE-03"], None, "Internal Service", "Critical", 1, "Authorization hold against checking balance"),
            (services["SVC-CARD-04"], None, vendors["VEND-CARD-04"], "ICT Third Party", "Critical", 2, "Visa Base I / Mastercard Banknet interface"),

            # Digital Banking Mobile depends on Payment Engine, Card, and Core Ledger
            (services["SVC-MBANK-05"], services["SVC-PAY-01"], None, "Internal Service", "Critical", 1, "P2P instant transfers and bill pay"),
            (services["SVC-MBANK-05"], services["SVC-CARD-04"], None, "Internal Service", "High", 2, "Card freeze and virtual card issuance"),
            (services["SVC-MBANK-05"], services["SVC-CORE-03"], None, "Internal Service", "Critical", 3, "Balance inquiries and transaction history"),

            # AML screener hooks into Payment Engine
            (services["SVC-PAY-01"], services["SVC-AML-06"], None, "Internal Service", "High", 4, "Pre-execution OFAC sanctions check"),

            # FX Trading depends on Refinitiv and Core Ledger
            (services["SVC-FX-07"], None, vendors["VEND-REFINITIV-06"], "ICT Third Party", "Critical", 1, "Streaming liquidity rates feed"),
            (services["SVC-FX-07"], services["SVC-CORE-03"], None, "Internal Service", "Critical", 2, "Treasury cash management ledger"),
        ]

        for src, dep, vendor, dep_type, crit, seq, notes in dependencies_data:
            ServiceDependency.objects.get_or_create(
                source_service=src,
                dependent_service=dep,
                third_party=vendor,
                defaults={
                    "dependency_type": dep_type,
                    "criticality": crit,
                    "recovery_sequence": seq,
                    "notes": notes
                }
            )

        # 4. Business Impact Analyses (BIA)
        bia_data = [
            (services["SVC-PAY-01"], "BIA-2027-PAY-01", "v2.1", "Attested", "Dr. Sarah Jenkins", 5, 5, 5, 5, "Catastrophic", 150000.00, "Statutory fines under PSD2/DORA for downtime > 2h. Severe liquidity impact."),
            (services["SVC-SWIFT-02"], "BIA-2027-SWF-02", "v2.0", "Attested", "Marcus Vance", 5, 4, 5, 4, "Catastrophic", 280000.00, "Overnight interbank settlement failures trigger Central Bank sanctions."),
            (services["SVC-CORE-03"], "BIA-2027-COR-03", "v3.0", "Attested", "Elena Rostova", 5, 5, 5, 5, "Catastrophic", 220000.00, "Total freeze of account balances, batch runs, and credit underwriting."),
            (services["SVC-CARD-04"], "BIA-2027-CRD-04", "v1.8", "Submitted", "David Chen", 4, 4, 3, 5, "Major", 175000.00, "High consumer complaints on social media within 15 minutes of card declines."),
            (services["SVC-MBANK-05"], "BIA-2027-MOB-05", "v1.5", "Attested", "Sophie Moreau", 3, 4, 2, 4, "Major", 65000.00, "App store ratings damage and customer helpline overload."),
            (services["SVC-AML-06"], "BIA-2027-AML-06", "v1.2", "Draft", "Tariq Al-Mansoor", 3, 3, 5, 3, "Major", 80000.00, "Risk of allowing prohibited transactions during degraded screening mode."),
            (services["SVC-FX-07"], "BIA-2027-TRD-07", "v2.2", "Attested", "Julian Blake", 5, 4, 4, 4, "Catastrophic", 310000.00, "Unhedged FX position volatility and regulatory reporting breaches under MiFID II."),
        ]

        for svc, ref, ver, status, assessor, fin, ops, reg, rep, crit, loss, exposure in bia_data:
            BusinessImpactAnalysis.objects.get_or_create(
                bia_reference=ref,
                defaults={
                    "service": svc,
                    "version": ver,
                    "status": status,
                    "assessor": assessor,
                    "financial_impact_score": fin,
                    "operational_impact_score": ops,
                    "regulatory_impact_score": reg,
                    "reputational_impact_score": rep,
                    "overall_criticality": crit,
                    "estimated_hourly_loss": loss,
                    "legal_regulatory_exposure": exposure,
                    "scope_details": f"Covers primary clusters, secondary cold standby, and failover APIs for {svc.name}.",
                    "attested_by": "Chief Risk Officer (CRO) Office" if status == "Attested" else "",
                    "attestation_date": date.today() - timedelta(days=30) if status == "Attested" else None,
                    "next_review_date": date.today() + timedelta(days=335)
                }
            )

        # 5. BC Plans & Emergency Contacts
        bcp_data = [
            (services["SVC-PAY-01"], "BCP-PAY-2027", "Real-Time Payment Engine Disaster Recovery Plan", "v2.4", "Approved",
             "Latency spike > 2500ms for 3 consecutive minutes, or unrecoverable primary AWS DB master failure.",
             "Automatic database failover to replica in AWS eu-west-1 (Ireland). Switch DNS traffic via Cloudflare within 8 minutes.",
             "1. Activate Incident Command Bridge.\n2. Verify health of Ireland warm replica.\n3. Trigger automated cutover pipeline in GitLab CI.\n4. Route traffic to secondary API gateway.\n5. Reconcile transaction in-flight ledger."),

            (services["SVC-CORE-03"], "BCP-CORE-2027", "Core Banking Enterprise Ledger Resilience Plan", "v3.1", "Approved",
             "Storage replication split-brain, total loss of Frankfurt Equinix FR5 data center facility.",
             "Active-Active Synchronous clustering between Frankfurt FR5 and Zurich ZH2. Quorum arbitrator at AWS EU.",
             "1. Declare disaster with Equinix NOC.\n2. Promote Zurich node to primary master.\n3. Notify SWIFT and Clearing House gateways of IP shift.\n4. Re-verify ledger checksum and audit balance."),

            (services["SVC-SWIFT-02"], "BCP-SWIFT-2027", "SWIFT Alliance Gateway Emergency Plan", "v2.0", "Approved",
             "Hardware Security Module (HSM) failure or loss of lease line to SWIFT secure network.",
             "Dual redundant VPN tunnel over Swisscom dedicated backup circuit to Zurich secondary HSM.",
             "1. Rotate cryptographic certificates.\n2. Reroute SWIFT Alliance gateway to secondary link.\n3. Perform ping loop test with SWIFT Brussels.\n4. Resume pending queue messages."),
        ]

        for svc, code, title, ver, status, trig, strat, steps in bcp_data:
            plan, _ = BCPlan.objects.get_or_create(
                plan_code=code,
                defaults={
                    "service": svc,
                    "title": title,
                    "version": ver,
                    "status": status,
                    "activation_threshold": trig,
                    "primary_site": "Equinix Frankfurt / AWS eu-central-1",
                    "dr_site": "Zurich Hot Standby / AWS eu-west-1",
                    "recovery_strategy": strat,
                    "failover_steps": steps,
                    "approved_by": "Head of Operational Resilience & CIO",
                    "approved_date": date.today() - timedelta(days=60),
                    "last_tested_date": date.today() - timedelta(days=20),
                }
            )

            # Contacts
            BCPEmergencyContact.objects.get_or_create(
                plan=plan,
                role_title="Incident Commander (Operations)",
                defaults={"contact_name": "Alexander Weber", "phone": "+49 69 1234 5001", "email": "a.weber@enterprise-bcm.bank", "priority": 1}
            )
            BCPEmergencyContact.objects.get_or_create(
                plan=plan,
                role_title="Lead Infrastructure Architect",
                defaults={"contact_name": "Ingrid Lindner", "phone": "+49 69 1234 5002", "email": "i.lindner@enterprise-bcm.bank", "priority": 2}
            )
            BCPEmergencyContact.objects.get_or_create(
                plan=plan,
                role_title="Regulatory Liaison / Compliance Officer",
                defaults={"contact_name": "Michael Thorne", "phone": "+44 20 7946 0991", "email": "m.thorne@enterprise-bcm.bank", "priority": 3, "is_alternate": True}
            )

        # 6. Scenarios
        scenarios_data = [
            ("SCN-CYBER-01", "Targeted Ransomware Lockdown of Primary Active Directory & Core Nodes", "Cyberattack", "Catastrophic",
             "A sophisticated zero-day lateral movement infects the internal management subnet, encrypting credential stores and triggering emergency isolation of payment clusters.",
             "T+00:00 EDR alerts anomaly on domain controller.\nT+00:15 Automated subnet quarantine isolates infected cluster.\nT+00:30 Manual declaration of Gold Incident.\nT+01:00 Verification of immutable WORM backups.\nT+02:00 Air-gapped bare metal rebuild sequence.",
             "Total cessation of internal administrative commands. Potential customer data compromise without immediate fail-safe isolation.",
             "Enforce air-gapped immutable backup restoration and automated cryptographic key rotation."),

            ("SCN-DC-02", "Primary Colocation Data Center (Frankfurt FR5) Extended Power Blackout", "Data Center Outage", "Catastrophic",
             "Substation transformer explosion followed by dual backup diesel generator fuel contamination causes complete power down of Frankfurt FR5.",
             "T+00:00 Utility grid drops.\nT+00:02 UPS batteries engage.\nT+00:12 Generator #2 fails.\nT+00:20 Auto-trigger of Zurich failover runbook.\nT+00:45 DNS repoint to Zurich hot DR.",
             "Hardware unavailable for minimum 48 hours. Latency to European clearing counterparties shifts +12ms.",
             "Hot standby active-active synchronous mirror in Zurich with automatic quorum arbitrator."),

            ("SCN-AWS-03", "AWS Europe Central (Frankfurt) Major Availability Zone Network Partition", "Cloud Outage", "High",
             "Undersea cable sever and regional border gateway protocol (BGP) routing loop cuts AWS Frankfurt eu-central-1 off from global internet.",
             "T+00:00 40% packet drop detected by Cloudflare health probes.\nT+00:05 Automated reroute to AWS Ireland eu-west-1.\nT+00:25 Read-replica promotion in Ireland.",
             "Customer mobile and web portal experience degraded performance for up to 15 minutes during route convergence.",
             "Multi-cloud and multi-region warm standby with automated latency-based DNS steering."),

            ("SCN-VEND-04", "SWIFT Alliance Third-Party Gateway Unplanned Extended Outage", "Supply Chain", "High",
             "Global maintenance error on SWIFT SAG infrastructure disables cross-border message queuing for 6 hours.",
             "T+00:00 Message queue rejection code 503 received.\nT+00:10 Escalate to SWIFT 24/7 Global Desk.\nT+00:30 Activate internal payment queue buffering.\nT+02:00 Regulatory disclosure to ECB.",
             "Inability to clear international wires; liquidity buildup in nostro settlement accounts.",
             "Local storage buffering for up to 24 hours with automatic replay upon link re-establishment.")
        ]

        scenarios = {}
        for code, title, cat, sev, desc, injects, impact, mit in scenarios_data:
            sc, _ = Scenario.objects.get_or_create(
                code=code,
                defaults={
                    "title": title,
                    "category": cat,
                    "severity": sev,
                    "description": desc,
                    "inject_timeline": injects,
                    "expected_impact": impact,
                    "recommended_mitigation": mit,
                    "is_approved": True
                }
            )
            scenarios[code] = sc

        # 7. RTEP Test Exercises
        tests_data = [
            ("EX-2027-Q1-PAY", "Real-Time Payment Failover Live Drill", scenarios["SCN-AWS-03"], services["SVC-PAY-01"], "Simulation Drill",
             timezone.now() - timedelta(days=12), "Ingrid Lindner", "Completed", "Successful", 60, 42,
             "Simulated 100% packet loss in AWS eu-central-1. Automated failover script initiated at T+04m. Ireland replica promoted at T+18m. Health probes green at T+42m. RTO Target was 60 minutes.",
             "Failover completed within 42 minutes, beating RTO of 60m. Minor delay in Redis cache synchronization noticed."),

            ("EX-2027-Q1-CORE", "Core Banking Zurich Disaster Recovery Failover", scenarios["SCN-DC-02"], services["SVC-CORE-03"], "Full Failover Test",
             timezone.now() - timedelta(days=25), "Alexander Weber", "Completed", "Partial Pass", 90, 84,
             "Frankfurt node powered down abruptly. Zurich quorum established. Transaction ledger replayed successfully. Two background reconciliation jobs aborted.",
             "RTO met (84m vs 90m allowed). However, secondary batch processing job took an additional 30 minutes to clean stale locks."),

            ("EX-2027-Q2-CYBER", "Simulated Enterprise Ransomware Air-Gap Recovery", scenarios["SCN-CYBER-01"], services["SVC-SWIFT-02"], "Tabletop Walkthrough",
             timezone.now() + timedelta(days=8), "Sarah Jenkins", "Scheduled", "Pending", 120, None, "", "")
        ]

        tests = {}
        for code, title, scn, svc, ex_type, sched, lead, status, outcome, tgt_rto, act_rto, log, obs in tests_data:
            t, _ = RTEPTestExercise.objects.get_or_create(
                test_code=code,
                defaults={
                    "title": title,
                    "scenario": scn,
                    "target_service": svc,
                    "exercise_type": ex_type,
                    "scheduled_date": sched,
                    "lead_facilitator": lead,
                    "status": status,
                    "outcome": outcome,
                    "target_rto_minutes": tgt_rto,
                    "actual_recovery_time_minutes": act_rto,
                    "execution_log": log,
                    "key_observations": obs,
                }
            )
            tests[code] = t

        # 8. Findings & Remediation (CAPA)
        findings_data = [
            ("FND-8801", "Secondary Redis Session Cache Sync Lagged by 14 Minutes During Failover", tests["EX-2027-Q1-PAY"], services["SVC-PAY-01"], "High",
             "Remediation In Progress", "Asynchronous replication backlog between AWS Frankfurt and Ireland.",
             "Upgrade cross-region inter-VPC connection to AWS Transit Gateway with 10Gbps dedicated pipe. Configure active Redis Enterprise bi-directional cluster.",
             "DevOps Lead: Carlos Mendes", date.today() + timedelta(days=21)),

            ("FND-8802", "Stale Lock on Batch Reconciliation Worker During Zurich Core Promotion", tests["EX-2027-Q1-CORE"], services["SVC-CORE-03"], "Critical",
             "Ready for Retest", "Database connection pool did not flush abandoned deadlocks on hard shutdown.",
             "Implement automatic lock timeout and dynamic connection pool eviction on node promotion event listener.",
             "DBA Lead: Elena Rostova", date.today() + timedelta(days=7)),

            ("FND-8803", "Emergency Call Tree SMS Notification Service Rate-Limited Under Peak Alert", None, services["SVC-MBANK-05"], "Medium",
             "Open", "Twilio notification endpoint was configured on tier-2 standard tier without dedicated shortcode throughput.",
             "Procure dedicated short-code carrier gateway with automated fall-back to AWS SNS and automated voice call tree.",
             "Security Ops: Dave Miller", date.today() + timedelta(days=45)),
        ]

        for code, title, test_obj, svc, sev, status, root, plan, assigned, due in findings_data:
            Finding.objects.get_or_create(
                finding_code=code,
                defaults={
                    "title": title,
                    "test_exercise": test_obj,
                    "service": svc,
                    "severity": sev,
                    "status": status,
                    "root_cause": root,
                    "remediation_plan": plan,
                    "assigned_to": assigned,
                    "due_date": due,
                }
            )

        # 9. Evidence Items
        evidence_data = [
            ("Q1 Payment Failover Execution Log & Prometheus Metrics", "Test Execution Log", services["SVC-PAY-01"], tests["EX-2027-Q1-PAY"], "failover_prom_metrics_q1_2027.json", 1450, "Ingrid Lindner", "v1.2"),
            ("Equinix Core Banking Zurich DR Switchover Signed Proof", "Failover Proof", services["SVC-CORE-03"], tests["EX-2027-Q1-CORE"], "zurich_dr_switchover_attestation.pdf", 3200, "Alexander Weber", "v1.0"),
            ("2027 Annual BIA Formal Attestation & Board Sign-off", "BIA Sign-Off Sheet", services["SVC-PAY-01"], None, "bia_board_signoff_q1_signed.pdf", 4800, "Chief Risk Officer", "v2.1"),
            ("SWIFT SAG Hardware Security Module Cryptographic Audit", "Audit Report", services["SVC-SWIFT-02"], None, "swift_hsm_audit_report_kpmg.pdf", 5120, "KPMG External Auditor", "v3.0"),
        ]

        for title, etype, svc, test_obj, fname, size, user, ver in evidence_data:
            EvidenceItem.objects.get_or_create(
                title=title,
                defaults={
                    "evidence_type": etype,
                    "service": svc,
                    "test_exercise": test_obj,
                    "file_name": fname,
                    "file_size_kb": size,
                    "uploaded_by": user,
                    "version": ver
                }
            )

        # 10. Approval Tasks (Workflow Engine)
        tasks_data = [
            ("TASK-APP-101", "Review & Attestation for Card Switch BIA (BIA-2027-CRD-04)", "BIA Assessment", "BIA-2027-CRD-04", "David Chen", "BCM Risk Director", "High", "Pending", "Annual periodic review of card transaction loss thresholds."),
            ("TASK-APP-102", "Approve Retest Results for Finding FND-8802 (Core Lock Eviction)", "Finding Closure Sign-off", "FND-8802", "Elena Rostova", "Head of Resilience", "Urgent", "Pending", "DBA has deployed hotfix build 4.19; awaiting approval to execute live retest."),
            ("TASK-APP-103", "Authorize Q2 Tabletop Ransomware Simulation Exercise", "Scenario Approval", "SCN-CYBER-01", "Sarah Jenkins", "Chief Information Security Officer", "Normal", "Approved", "Scenario approved with inclusion of cloud identity tenant isolation injects."),
        ]

        for code, title, itype, ref, req, assign, prio, status, comments in tasks_data:
            ApprovalTask.objects.get_or_create(
                task_code=code,
                defaults={
                    "title": title,
                    "item_type": itype,
                    "reference_id": ref,
                    "requested_by": req,
                    "assigned_to": assign,
                    "priority": prio,
                    "status": status,
                    "comments": comments
                }
            )

        # 11. Audit Log Entries
        audit_data = [
            ("Ingrid Lindner", "Executed Drill", "RTEPTestExercise", "EX-2027-Q1-PAY", "Completed payment failover test in 42 minutes. Target RTO satisfied."),
            ("Elena Rostova", "Updated Remediation Status", "Finding", "FND-8802", "Marked finding as Ready for Retest with code fix commit #99a21."),
            ("Dr. Sarah Jenkins", "Attested BIA", "BusinessImpactAnalysis", "BIA-2027-PAY-01", "Formally attested payment impact scores and PSD2 regulatory disclosure."),
            ("David Chen", "Submitted for Approval", "ApprovalTask", "TASK-APP-101", "Routed card processing BIA to risk review queue."),
            ("System Resilience Monitor", "Triggered Synthetic Probe", "CriticalService", "SVC-CORE-03", "Automated latency probe completed across all primary and DR nodes (18ms)."),
        ]

        for user, act, etype, eid, details in audit_data:
            AuditLogEntry.objects.create(
                user=user,
                action=act,
                entity_type=etype,
                entity_id=eid,
                details=details,
                ip_address="10.24.8.102"
            )

        # 12. Notifications
        notif_data = [
            ("Critical Finding FND-8802 Ready for Retest", "DBA team has patched database connection pool stale locks for Core Banking Ledger.", "Alert"),
            ("Approval Queue: 2 Pending Attestations", "You have 2 pending approval tasks requiring sign-off before end of week.", "Approval"),
            ("Upcoming Drill: Ransomware Tabletop in 8 Days", "RTEP exercise EX-2027-Q2-CYBER scheduled with Gold Team crisis participants.", "Exercise"),
            ("DORA Compliance Audit Notice", "ICT Third-Party register review required for Equinix and AWS by end of quarter.", "Compliance"),
        ]

        for title, msg, ntype in notif_data:
            Notification.objects.get_or_create(
                title=title,
                defaults={"message": msg, "notification_type": ntype, "is_read": False}
            )

        # 13. ResQ AI Chat Pre-populated Q&A for demo
        chat_data = [
            ("What services are affected if AWS Frankfurt eu-central-1 experiences a catastrophic outage?",
             "Analyzing dependency graph... If AWS Frankfurt fails, the following services face immediate or cascading impact:\n1. SVC-PAY-01 (Real-Time Payment Engine) - Direct dependency. RTO: 1.0 hr. Financial exposure: $150,000/hr.\n2. SVC-MBANK-05 (Mobile & Web Banking) - Cascading dependency via payment APIs.\nRecommended Action: Activate BCP-PAY-2027 to execute DNS traffic cutover to AWS Ireland (eu-west-1) replica within 8 minutes.",
             "SVC-PAY-01, SVC-MBANK-05"),
            ("Show me all Tier 1 services with RTO under 2 hours",
             "Here are your Tier 1 critical services with RTO <= 2.0 hours:\n• SVC-PAY-01: Real-Time Payment Engine (RTO: 1.0h, RPO: 0.0h)\n• SVC-CARD-04: Card Issuing & ATM Switch (RTO: 1.0h, RPO: 0.2h)\n• SVC-FX-07: FX & Treasury Trading (RTO: 1.0h, RPO: 0.1h)\n• SVC-CORE-03: Core Banking Account Ledger (RTO: 1.5h, RPO: 0.25h)\n• SVC-SWIFT-02: SWIFT Cross-Border Clearing (RTO: 2.0h, RPO: 0.5h)\nAll 5 services have verified BCPs and active DR configurations.",
             "SVC-PAY-01, SVC-CARD-04, SVC-FX-07, SVC-CORE-03, SVC-SWIFT-02")
        ]

        for q, ans, matches in chat_data:
            ResQChatLog.objects.get_or_create(
                user_query=q,
                defaults={"ai_response": ans, "matched_services": matches, "feedback_positive": True}
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded enterprise BCM sample database!"))
