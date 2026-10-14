from django.db import models
from django.utils import timezone

class CriticalService(models.Model):
    TIER_CHOICES = [
        ('Tier 1', 'Tier 1 - Mission Critical'),
        ('Tier 2', 'Tier 2 - Business Critical'),
        ('Tier 3', 'Tier 3 - Important / Operational'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Under Review', 'Under Review'),
        ('Onboarding', 'Onboarding'),
        ('Retired', 'Retired'),
    ]

    code = models.CharField(max_length=32, unique=True, help_text="e.g. SVC-PAY-01")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='Tier 1')
    owner_name = models.CharField(max_length=120)
    department = models.CharField(max_length=120)
    rto_hours = models.FloatField(help_text="Recovery Time Objective in hours", default=2.0)
    rpo_hours = models.FloatField(help_text="Recovery Point Objective in hours", default=0.5)
    mtpd_hours = models.FloatField(help_text="Maximum Tolerable Period of Disruption in hours", default=4.0)
    financial_loss_per_hour = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    last_bia_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tier', 'code']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.tier})"


class ICTThirdParty(models.Model):
    CRITICALITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Under Audit', 'Under Audit'),
        ('Conditional', 'Conditional'),
    ]

    vendor_code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    service_provided = models.CharField(max_length=255)
    criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='Critical')
    contact_email = models.EmailField(blank=True)
    sla_percentage = models.FloatField(default=99.95, help_text="SLA uptime percentage")
    hosting_region = models.CharField(max_length=120, default='Primary Cloud (AWS us-east-1)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    dora_compliant = models.BooleanField(default=True, help_text="Digital Operational Resilience Act compliant")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "ICT Third Parties"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.service_provided})"


class ServiceDependency(models.Model):
    TYPE_CHOICES = [
        ('Internal Service', 'Internal Service'),
        ('ICT Third Party', 'ICT Third Party / Cloud Provider'),
        ('Data Pipeline', 'Data Pipeline / Database'),
        ('Facility / Data Center', 'Facility / Data Center'),
    ]
    CRITICALITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Moderate', 'Moderate'),
    ]

    source_service = models.ForeignKey(CriticalService, related_name='downstream_dependencies', on_delete=models.CASCADE)
    dependent_service = models.ForeignKey(CriticalService, related_name='upstream_dependencies', on_delete=models.CASCADE, null=True, blank=True)
    third_party = models.ForeignKey(ICTThirdParty, related_name='service_links', on_delete=models.SET_NULL, null=True, blank=True)
    dependency_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default='Internal Service')
    criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='Critical')
    recovery_sequence = models.PositiveIntegerField(default=1, help_text="Sequence in recovery order")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Service Dependencies"

    def __str__(self):
        target = self.dependent_service.name if self.dependent_service else (self.third_party.name if self.third_party else 'None')
        return f"{self.source_service.code} -> {target} ({self.dependency_type})"


class BusinessImpactAnalysis(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Submitted', 'Submitted for Review'),
        ('Attested', 'Attested & Approved'),
        ('Expired', 'Requires Periodic Review'),
    ]
    CRITICALITY_RATING = [
        ('Catastrophic', 'Catastrophic'),
        ('Major', 'Major'),
        ('Moderate', 'Moderate'),
        ('Minor', 'Minor'),
    ]

    service = models.ForeignKey(CriticalService, related_name='bias', on_delete=models.CASCADE)
    bia_reference = models.CharField(max_length=32, unique=True)
    version = models.CharField(max_length=16, default="v1.0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Submitted')
    assessor = models.CharField(max_length=120)
    financial_impact_score = models.IntegerField(default=4, help_text="1 (Low) to 5 (Critical)")
    operational_impact_score = models.IntegerField(default=5, help_text="1 (Low) to 5 (Critical)")
    regulatory_impact_score = models.IntegerField(default=4, help_text="1 (Low) to 5 (Critical)")
    reputational_impact_score = models.IntegerField(default=5, help_text="1 (Low) to 5 (Critical)")
    overall_criticality = models.CharField(max_length=20, choices=CRITICALITY_RATING, default='Major')
    peak_impact_timeframe = models.CharField(max_length=255, default="Business Hours & Month-End Reconciliation")
    estimated_hourly_loss = models.DecimalField(max_digits=12, decimal_places=2, default=75000.00)
    legal_regulatory_exposure = models.TextField(blank=True)
    scope_details = models.TextField(blank=True)
    attested_by = models.CharField(max_length=120, blank=True)
    attestation_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business Impact Analyses"
        ordering = ['-updated_at']

    def calculate_score(self):
        total = self.financial_impact_score + self.operational_impact_score + self.regulatory_impact_score + self.reputational_impact_score
        avg = total / 4.0
        if avg >= 4.2:
            return 'Catastrophic'
        elif avg >= 3.2:
            return 'Major'
        elif avg >= 2.2:
            return 'Moderate'
        return 'Minor'

    def __str__(self):
        return f"{self.bia_reference} - {self.service.name} ({self.version})"


class BCPlan(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending Approval', 'Pending Approval'),
        ('Approved', 'Approved & Active'),
        ('Under Revision', 'Under Revision'),
    ]

    service = models.ForeignKey(CriticalService, related_name='bc_plans', on_delete=models.CASCADE)
    plan_code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=16, default="v2.0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Approved')
    activation_threshold = models.TextField(help_text="Triggers for activating the BCP")
    primary_site = models.CharField(max_length=150, default="Primary Data Center (Tier IV Frankfurt)")
    dr_site = models.CharField(max_length=150, default="DR Hot Site (Tier IV Zurich)")
    recovery_strategy = models.TextField()
    failover_steps = models.TextField(help_text="Detailed chronological failover sequence")
    approved_by = models.CharField(max_length=120, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    last_tested_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Business Continuity Plans"
        ordering = ['plan_code']

    def __str__(self):
        return f"{self.plan_code}: {self.title} ({self.version})"


class BCPEmergencyContact(models.Model):
    plan = models.ForeignKey(BCPlan, related_name='emergency_contacts', on_delete=models.CASCADE)
    role_title = models.CharField(max_length=120, help_text="e.g. Incident Commander, Lead Database Admin")
    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    priority = models.PositiveIntegerField(default=1)
    is_alternate = models.BooleanField(default=False)

    class Meta:
        ordering = ['priority']

    def __str__(self):
        return f"{self.role_title}: {self.contact_name}"


class Scenario(models.Model):
    CATEGORY_CHOICES = [
        ('Cyberattack', 'Cyberattack / Ransomware'),
        ('Data Center Outage', 'Data Center Infrastructure Failure'),
        ('Cloud Outage', 'Cloud Provider Regional Outage'),
        ('Supply Chain', 'Third Party / Vendor Disruption'),
        ('Facility Inaccessibility', 'Facility Inaccessibility / Natural Disaster'),
    ]
    SEVERITY_CHOICES = [
        ('Catastrophic', 'Catastrophic'),
        ('High', 'High'),
        ('Moderate', 'Moderate'),
    ]

    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='Cyberattack')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='High')
    description = models.TextField()
    inject_timeline = models.TextField(help_text="Chronological injects for simulation or exercise")
    expected_impact = models.TextField()
    recommended_mitigation = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class RTEPTestExercise(models.Model):
    TYPE_CHOICES = [
        ('Simulation Drill', 'Simulation Drill'),
        ('Tabletop Walkthrough', 'Tabletop Walkthrough'),
        ('Full Failover Test', 'Full Failover Test'),
        ('Component Recovery Drill', 'Component Recovery Drill'),
    ]
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    OUTCOME_CHOICES = [
        ('Pending', 'Pending Execution'),
        ('Successful', 'Successful (RTO & RPO Met)'),
        ('Partial Pass', 'Partial Pass (Minor Breaches)'),
        ('Failed', 'Failed (RTO Exceeded)'),
    ]

    test_code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    scenario = models.ForeignKey(Scenario, related_name='tests', on_delete=models.CASCADE)
    target_service = models.ForeignKey(CriticalService, related_name='test_drills', on_delete=models.CASCADE)
    exercise_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default='Simulation Drill')
    scheduled_date = models.DateTimeField()
    lead_facilitator = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='Pending')
    target_rto_minutes = models.PositiveIntegerField(default=120)
    actual_recovery_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    execution_log = models.TextField(blank=True)
    key_observations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "RTEP Test Exercise"
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.test_code} - {self.title}"


class Finding(models.Model):
    SEVERITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Remediation In Progress', 'Remediation In Progress'),
        ('Ready for Retest', 'Ready for Retest'),
        ('Closed & Verified', 'Closed & Verified'),
    ]

    finding_code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    test_exercise = models.ForeignKey(RTEPTestExercise, related_name='findings', on_delete=models.SET_NULL, null=True, blank=True)
    service = models.ForeignKey(CriticalService, related_name='findings', on_delete=models.CASCADE)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='High')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Open')
    root_cause = models.TextField()
    remediation_plan = models.TextField()
    assigned_to = models.CharField(max_length=120)
    due_date = models.DateField()
    retest_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.finding_code} - {self.title} [{self.severity}]"


class EvidenceItem(models.Model):
    EVIDENCE_TYPES = [
        ('Test Execution Log', 'Test Execution Log'),
        ('Failover Proof', 'Failover Proof / Metrics'),
        ('BIA Sign-Off Sheet', 'BIA Sign-Off Sheet'),
        ('Audit Report', 'Audit Report'),
        ('Architecture Lineage', 'Architecture Lineage Diagram'),
    ]

    title = models.CharField(max_length=255)
    evidence_type = models.CharField(max_length=40, choices=EVIDENCE_TYPES, default='Test Execution Log')
    service = models.ForeignKey(CriticalService, related_name='evidence_docs', on_delete=models.SET_NULL, null=True, blank=True)
    test_exercise = models.ForeignKey(RTEPTestExercise, related_name='evidence_docs', on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_size_kb = models.IntegerField(default=520)
    uploaded_by = models.CharField(max_length=120)
    version = models.CharField(max_length=16, default="v1.0")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.evidence_type})"


class ApprovalTask(models.Model):
    ITEM_TYPES = [
        ('BIA Assessment', 'BIA Assessment'),
        ('Business Continuity Plan', 'Business Continuity Plan'),
        ('Scenario Approval', 'Scenario Approval'),
        ('Finding Closure Sign-off', 'Finding Closure Sign-off'),
        ('Access Delegation', 'Access Delegation'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Delegated', 'Delegated'),
    ]
    PRIORITY_CHOICES = [
        ('Urgent', 'Urgent'),
        ('High', 'High'),
        ('Normal', 'Normal'),
    ]

    task_code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    item_type = models.CharField(max_length=35, choices=ITEM_TYPES)
    reference_id = models.CharField(max_length=64, help_text="e.g. BIA-2027-01 or BCP-PAY-01")
    requested_by = models.CharField(max_length=120)
    assigned_to = models.CharField(max_length=120)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='High')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    comments = models.TextField(blank=True)
    submitted_date = models.DateTimeField(auto_now_add=True)
    actioned_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_date']

    def __str__(self):
        return f"{self.task_code} - {self.title} ({self.status})"


class AuditLogEntry(models.Model):
    user = models.CharField(max_length=120)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=64)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(default="10.24.8.102")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Audit Log Entries"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user} - {self.action} on {self.entity_type} {self.entity_id}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('Alert', 'Critical Alert'),
        ('Approval', 'Pending Approval'),
        ('Exercise', 'Exercise Reminder'),
        ('Compliance', 'Compliance Notice'),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Alert')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ResQChatLog(models.Model):
    user_query = models.TextField()
    ai_response = models.TextField()
    matched_services = models.CharField(max_length=255, blank=True)
    feedback_positive = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Query: {self.user_query[:50]}"
