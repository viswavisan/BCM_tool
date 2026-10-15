import json
from datetime import datetime, date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

from .models import (
    CriticalService, ICTThirdParty, ServiceDependency,
    BusinessImpactAnalysis, BCPlan, BCPEmergencyContact,
    Scenario, RTEPTestExercise, Finding, EvidenceItem,
    ApprovalTask, AuditLogEntry, Notification, ResQChatLog,
    UserProfile, RoleDefinition
)

# ----------------- Navigation Context Processor / Helper -----------------
def get_global_context(request=None):
    unread_notifications = Notification.objects.filter(is_read=False).count()
    pending_approvals = ApprovalTask.objects.filter(status='Pending').count()
    
    current_user = None
    user_profile = None
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        current_user = request.user
        try:
            user_profile = request.user.profile
        except:
            user_profile = None

    return {
        'unread_notifications': unread_notifications,
        'pending_approvals': pending_approvals,
        'current_time': timezone.now(),
        'system_status': 'Operational - All Rings Normal',
        'current_user': current_user,
        'user_profile': user_profile,
    }


# ----------------- Authentication & User Management (Milestone 1, APIs 83-86) -----------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'

    if request.method == 'POST':
        action = request.POST.get('action', 'credentials')

        # 1. Quick demo login or simulated enterprise SSO
        if action in ['quick_login', 'sso_login']:
            username = request.POST.get('username') or 'cro_officer'
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.first()
            if user:
                login(request, user)
                auth_mode = "Enterprise SSO (Okta SAML 2.0)" if action == 'sso_login' else "Demo Persona Credentials"
                AuditLogEntry.objects.create(
                    user=user.get_full_name() or user.username,
                    action='User Authenticated',
                    entity_type='User',
                    entity_id=user.username,
                    details=f"Secure session created via {auth_mode}.",
                    ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
                )
                role_label = getattr(user, 'profile', None) and user.profile.role or 'Resilience Lead'
                messages.success(request, f"Welcome back, {user.get_full_name() or user.username}! Logged in as {role_label}.")
                return redirect(next_url)

        # 2. Standard username/password login
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            AuditLogEntry.objects.create(
                user=user.get_full_name() or user.username,
                action='User Authenticated',
                entity_type='User',
                entity_id=user.username,
                details="Authenticated with enterprise credentials and multi-factor validation.",
                ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
            )
            messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please use valid credentials or choose a quick-demo persona below.")

    demo_personas = [
        {"username": "cro_officer", "name": "Dr. Alistair Vance", "role": "Chief Risk & Resilience Officer (CRO)", "dept": "Executive Risk Office", "badge": "Executive Sign-Off", "color": "#ef4444"},
        {"username": "bcm_manager", "name": "Sarah Jenkins", "role": "Enterprise BCM Lead", "dept": "Operational Resilience", "badge": "BIA & BCP Authoring", "color": "#10b981"},
        {"username": "service_owner", "name": "David Chen", "role": "Critical Service Owner", "dept": "Payments & Retail Rails", "badge": "Service Lead", "color": "#06b6d4"},
        {"username": "auditor", "name": "Marcus Thorne", "role": "Regulatory & Internal Auditor", "dept": "Compliance Assurance", "badge": "Audit & Review", "color": "#8b5cf6"},
        {"username": "admin", "name": "Resilience Administrator", "role": "Resilience Administrator", "dept": "Enterprise Architecture", "badge": "Full Administration", "color": "#6366f1"},
    ]

    return render(request, 'bcm_app/login.html', {
        'next_url': next_url,
        'demo_personas': demo_personas
    })


def logout_view(request):
    if request.user.is_authenticated:
        AuditLogEntry.objects.create(
            user=request.user.get_full_name() or request.user.username,
            action='User Logout',
            entity_type='User',
            entity_id=request.user.username,
            details="User ended active session.",
            ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
        )
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('login')


@login_required
def user_profile_view(request):
    ctx = get_global_context(request)
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        dept = request.POST.get('department', '').strip()
        role = request.POST.get('role', '').strip()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        profile.phone = phone
        profile.department = dept
        if role:
            profile.role = role
        profile.save()

        AuditLogEntry.objects.create(
            user=user.get_full_name() or user.username,
            action='Updated User Profile',
            entity_type='UserProfile',
            entity_id=user.username,
            details="Updated user profile details and contact parameters."
        )
        messages.success(request, "User profile updated successfully.")
        return redirect('user_profile')

    ctx.update({
        'profile_user': user,
        'profile': profile,
        'active_menu': 'profile'
    })
    return render(request, 'bcm_app/user_profile.html', ctx)


# ----------------- 1. Dashboards -----------------
@login_required
def dashboard_view(request):
    ctx = get_global_context(request)

    
    total_services = CriticalService.objects.count()
    tier1_services = CriticalService.objects.filter(tier='Tier 1').count()
    tier2_services = CriticalService.objects.filter(tier='Tier 2').count()
    tier3_services = CriticalService.objects.filter(tier='Tier 3').count()
    
    total_bias = BusinessImpactAnalysis.objects.count()
    attested_bias = BusinessImpactAnalysis.objects.filter(status='Attested').count()
    bia_compliance_pct = int((attested_bias / total_bias * 100)) if total_bias > 0 else 0
    
    approved_bcps = BCPlan.objects.filter(status='Approved').count()
    open_findings = Finding.objects.exclude(status='Closed & Verified').count()
    critical_findings = Finding.objects.filter(severity='Critical').exclude(status='Closed & Verified').count()
    
    recent_tasks = ApprovalTask.objects.filter(status='Pending')[:5]
    recent_drills = RTEPTestExercise.objects.all()[:4]
    notifications = Notification.objects.all()[:6]
    
    # Financial aggregate
    total_hourly_loss = sum(s.financial_loss_per_hour for s in CriticalService.objects.all())
    
    # Chart data
    tier_chart_labels = ['Tier 1 (Mission Critical)', 'Tier 2 (Business Critical)', 'Tier 3 (Important)']
    tier_chart_data = [tier1_services, tier2_services, tier3_services]
    
    bia_chart_labels = ['Attested', 'Under Review / Submitted', 'Draft / Overdue']
    bia_chart_data = [
        BusinessImpactAnalysis.objects.filter(status='Attested').count(),
        BusinessImpactAnalysis.objects.filter(status='Submitted').count(),
        BusinessImpactAnalysis.objects.filter(Q(status='Draft') | Q(status='Expired')).count(),
    ]
    
    findings_severity_data = [
        Finding.objects.filter(severity='Critical').count(),
        Finding.objects.filter(severity='High').count(),
        Finding.objects.filter(severity='Medium').count(),
        Finding.objects.filter(severity='Low').count(),
    ]
    
    ctx.update({
        'total_services': total_services,
        'tier1_services': tier1_services,
        'bia_compliance_pct': bia_compliance_pct,
        'approved_bcps': approved_bcps,
        'open_findings': open_findings,
        'critical_findings': critical_findings,
        'total_hourly_loss': total_hourly_loss,
        'recent_tasks': recent_tasks,
        'recent_drills': recent_drills,
        'notifications': notifications,
        'tier_chart_labels_json': json.dumps(tier_chart_labels),
        'tier_chart_data_json': json.dumps(tier_chart_data),
        'bia_chart_labels_json': json.dumps(bia_chart_labels),
        'bia_chart_data_json': json.dumps(bia_chart_data),
        'findings_severity_data_json': json.dumps(findings_severity_data),
        'active_menu': 'dashboard'
    })
    return render(request, 'bcm_app/dashboard.html', ctx)


# ----------------- 2. Critical Services Registry -----------------
@login_required
def services_list_view(request):
    ctx = get_global_context(request)
    tier_filter = request.GET.get('tier', '')
    query = request.GET.get('q', '')
    
    services = CriticalService.objects.all()
    if tier_filter:
        services = services.filter(tier=tier_filter)
    if query:
        services = services.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(department__icontains=query))
        
    if request.method == 'POST':
        # Add new service
        code = request.POST.get('code')
        name = request.POST.get('name')
        tier = request.POST.get('tier', 'Tier 1')
        owner = request.POST.get('owner_name')
        dept = request.POST.get('department')
        rto = float(request.POST.get('rto_hours', 2.0))
        rpo = float(request.POST.get('rpo_hours', 0.5))
        mtpd = float(request.POST.get('mtpd_hours', 4.0))
        loss = float(request.POST.get('financial_loss_per_hour', 50000.0))
        desc = request.POST.get('description', '')
        
        svc = CriticalService.objects.create(
            code=code, name=name, tier=tier, owner_name=owner,
            department=dept, rto_hours=rto, rpo_hours=rpo,
            mtpd_hours=mtpd, financial_loss_per_hour=loss,
            description=desc, status='Active'
        )
        AuditLogEntry.objects.create(
            user='Administrator', action='Created Critical Service',
            entity_type='CriticalService', entity_id=svc.code,
            details=f"Onboarded service {svc.name} under {svc.tier} with RTO {svc.rto_hours}h"
        )
        messages.success(request, f"Service {svc.code} successfully registered.")
        return redirect('services_list')

    ctx.update({
        'services': services,
        'tier_filter': tier_filter,
        'query': query,
        'active_menu': 'services'
    })
    return render(request, 'bcm_app/services_list.html', ctx)


@login_required
def service_detail_view(request, service_id):
    ctx = get_global_context(request)
    service = get_object_or_404(CriticalService, id=service_id)
    
    bias = service.bias.all()
    bcps = service.bc_plans.all()
    downstream = service.downstream_dependencies.all()
    upstream = service.upstream_dependencies.all()
    tests = service.test_drills.all()
    findings = service.findings.all()
    evidence = service.evidence_docs.all()
    
    ctx.update({
        'service': service,
        'bias': bias,
        'bcps': bcps,
        'downstream': downstream,
        'upstream': upstream,
        'tests': tests,
        'findings': findings,
        'evidence': evidence,
        'active_menu': 'services'
    })
    return render(request, 'bcm_app/service_detail.html', ctx)


@login_required
def ict_third_party_view(request):
    ctx = get_global_context(request)
    vendors = ICTThirdParty.objects.all()
    
    if request.method == 'POST':
        code = request.POST.get('vendor_code')
        name = request.POST.get('name')
        svc = request.POST.get('service_provided')
        crit = request.POST.get('criticality', 'High')
        email = request.POST.get('contact_email')
        sla = float(request.POST.get('sla_percentage', 99.95))
        region = request.POST.get('hosting_region')
        
        v = ICTThirdParty.objects.create(
            vendor_code=code, name=name, service_provided=svc,
            criticality=crit, contact_email=email, sla_percentage=sla,
            hosting_region=region, status='Active', dora_compliant=True
        )
        AuditLogEntry.objects.create(
            user='BCM Officer', action='Added Third-Party Vendor',
            entity_type='ICTThirdParty', entity_id=v.vendor_code,
            details=f"Registered vendor {v.name} ({v.service_provided}) under DORA register."
        )
        messages.success(request, f"ICT Vendor {v.name} added to third-party register.")
        return redirect('ict_third_party')

    ctx.update({
        'vendors': vendors,
        'active_menu': 'third_party'
    })
    return render(request, 'bcm_app/ict_third_party.html', ctx)


# ----------------- 3. Business Impact Analysis (BIA) -----------------
@login_required
def bia_list_view(request):
    ctx = get_global_context(request)
    bias = BusinessImpactAnalysis.objects.select_related('service').all()
    services = CriticalService.objects.all()
    
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        service = get_object_or_404(CriticalService, id=service_id)
        ref = request.POST.get('bia_reference') or f"BIA-2027-{service.code.split('-')[-1]}"
        assessor = request.POST.get('assessor', 'Operational Risk Officer')
        fin = int(request.POST.get('financial_impact_score', 4))
        ops = int(request.POST.get('operational_impact_score', 4))
        reg = int(request.POST.get('regulatory_impact_score', 4))
        rep = int(request.POST.get('reputational_impact_score', 4))
        loss = float(request.POST.get('estimated_hourly_loss', 50000.0))
        timeframe = request.POST.get('peak_impact_timeframe', 'Standard Trading Hours')
        exposure = request.POST.get('legal_regulatory_exposure', '')
        
        bia = BusinessImpactAnalysis(
            service=service, bia_reference=ref, version="v1.0",
            status="Submitted", assessor=assessor,
            financial_impact_score=fin, operational_impact_score=ops,
            regulatory_impact_score=reg, reputational_impact_score=rep,
            estimated_hourly_loss=loss, peak_impact_timeframe=timeframe,
            legal_regulatory_exposure=exposure
        )
        bia.overall_criticality = bia.calculate_score()
        bia.save()
        
        # Create approval task
        ApprovalTask.objects.create(
            task_code=f"TASK-BIA-{bia.id}",
            title=f"Attestation Required for BIA {bia.bia_reference} ({service.name})",
            item_type="BIA Assessment",
            reference_id=bia.bia_reference,
            requested_by=assessor,
            assigned_to="Chief Risk Officer (CRO) Office",
            priority="High",
            status="Pending",
            comments="New BIA assessment submitted for executive attestation."
        )
        
        AuditLogEntry.objects.create(
            user=assessor, action='Submitted BIA',
            entity_type='BusinessImpactAnalysis', entity_id=bia.bia_reference,
            details=f"Submitted assessment for {service.name} with score {bia.overall_criticality}"
        )
        messages.success(request, f"BIA {bia.bia_reference} submitted for review.")
        return redirect('bia_list')

    ctx.update({
        'bias': bias,
        'services': services,
        'active_menu': 'bia'
    })
    return render(request, 'bcm_app/bia_list.html', ctx)


@login_required
def bia_detail_view(request, bia_id):
    ctx = get_global_context(request)
    bia = get_object_or_404(BusinessImpactAnalysis, id=bia_id)
    
    radar_labels = ['Financial Impact', 'Operational Impact', 'Regulatory Impact', 'Reputational Impact']
    radar_data = [
        bia.financial_impact_score,
        bia.operational_impact_score,
        bia.regulatory_impact_score,
        bia.reputational_impact_score
    ]
    
    ctx.update({
        'bia': bia,
        'radar_labels_json': json.dumps(radar_labels),
        'radar_data_json': json.dumps(radar_data),
        'active_menu': 'bia'
    })
    return render(request, 'bcm_app/bia_detail.html', ctx)


@login_required
def bia_attest_view(request, bia_id):
    if request.method == 'POST':
        bia = get_object_or_404(BusinessImpactAnalysis, id=bia_id)
        bia.status = 'Attested'
        bia.attested_by = request.POST.get('attested_by', 'Chief Risk Officer')
        bia.attestation_date = date.today()
        bia.next_review_date = date.today() + timedelta(days=365)
        bia.save()
        
        # Mark related approval task as approved
        ApprovalTask.objects.filter(reference_id=bia.bia_reference).update(status='Approved', actioned_date=timezone.now())
        
        AuditLogEntry.objects.create(
            user=bia.attested_by, action='Attested BIA',
            entity_type='BusinessImpactAnalysis', entity_id=bia.bia_reference,
            details=f"Formally attested BIA for {bia.service.name}. Next review scheduled for {bia.next_review_date}."
        )
        messages.success(request, f"BIA {bia.bia_reference} successfully attested and approved.")
        return redirect('bia_detail', bia_id=bia.id)
    return redirect('bia_list')


# ----------------- 4. Dependencies & Lineage Graph -----------------
@login_required
def dependencies_graph_view(request):
    ctx = get_global_context(request)
    services = CriticalService.objects.all()
    vendors = ICTThirdParty.objects.all()
    dependencies = ServiceDependency.objects.select_related('source_service', 'dependent_service', 'third_party').all()
    
    ctx.update({
        'services': services,
        'vendors': vendors,
        'dependencies': dependencies,
        'active_menu': 'dependencies'
    })
    return render(request, 'bcm_app/dependencies_graph.html', ctx)


@login_required
def api_dependencies_graph(request):
    services = CriticalService.objects.all()
    vendors = ICTThirdParty.objects.all()
    dependencies = ServiceDependency.objects.all()
    
    nodes = []
    for s in services:
        nodes.append({
            'id': f"svc_{s.id}",
            'label': s.code,
            'name': s.name,
            'type': 'service',
            'tier': s.tier,
            'rto': s.rto_hours,
            'color': '#ef4444' if s.tier == 'Tier 1' else ('#f59e0b' if s.tier == 'Tier 2' else '#10b981')
        })
    for v in vendors:
        nodes.append({
            'id': f"vend_{v.id}",
            'label': v.vendor_code,
            'name': v.name,
            'type': 'vendor',
            'tier': v.criticality,
            'rto': 'External',
            'color': '#6366f1'
        })
        
    links = []
    for d in dependencies:
        source_id = f"svc_{d.source_service.id}"
        if d.dependent_service:
            target_id = f"svc_{d.dependent_service.id}"
        elif d.third_party:
            target_id = f"vend_{d.third_party.id}"
        else:
            continue
            
        links.append({
            'source': source_id,
            'target': target_id,
            'type': d.dependency_type,
            'criticality': d.criticality,
            'notes': d.notes
        })
        
    return JsonResponse({'nodes': nodes, 'links': links})


# ----------------- 5. Business Continuity Plans (BCP) -----------------
@login_required
def bcp_list_view(request):
    ctx = get_global_context(request)
    plans = BCPlan.objects.select_related('service').prefetch_related('emergency_contacts').all()
    services = CriticalService.objects.all()
    
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        service = get_object_or_404(CriticalService, id=service_id)
        code = request.POST.get('plan_code')
        title = request.POST.get('title')
        threshold = request.POST.get('activation_threshold')
        strategy = request.POST.get('recovery_strategy')
        steps = request.POST.get('failover_steps')
        primary = request.POST.get('primary_site', 'Primary Data Center')
        dr = request.POST.get('dr_site', 'Secondary DR Facility')
        
        plan = BCPlan.objects.create(
            service=service, plan_code=code, title=title,
            version="v1.0", status="Approved",
            activation_threshold=threshold, recovery_strategy=strategy,
            failover_steps=steps, primary_site=primary, dr_site=dr,
            approved_by="Resilience Steering Committee", approved_date=date.today()
        )
        AuditLogEntry.objects.create(
            user='BCM Manager', action='Published BCP',
            entity_type='BCPlan', entity_id=plan.plan_code,
            details=f"Published Business Continuity Plan for {service.name}."
        )
        messages.success(request, f"BC Plan {plan.plan_code} successfully created.")
        return redirect('bcp_list')

    ctx.update({
        'plans': plans,
        'services': services,
        'active_menu': 'bcp'
    })
    return render(request, 'bcm_app/bcp_list.html', ctx)


@login_required
def bcp_detail_view(request, bcp_id):
    ctx = get_global_context(request)
    plan = get_object_or_404(BCPlan, id=bcp_id)
    contacts = plan.emergency_contacts.all()
    
    if request.method == 'POST':
        # Add emergency contact
        role = request.POST.get('role_title')
        name = request.POST.get('contact_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        prio = int(request.POST.get('priority', 1))
        alt = bool(request.POST.get('is_alternate'))
        
        contact = BCPEmergencyContact.objects.create(
            plan=plan, role_title=role, contact_name=name,
            phone=phone, email=email, priority=prio, is_alternate=alt
        )
        messages.success(request, f"Emergency Contact {contact.contact_name} added to call tree.")
        return redirect('bcp_detail', bcp_id=plan.id)

    ctx.update({
        'plan': plan,
        'contacts': contacts,
        'active_menu': 'bcp'
    })
    return render(request, 'bcm_app/bcp_detail.html', ctx)


# ----------------- 6. Scenario Library & RTEP Testing -----------------
@login_required
def scenarios_list_view(request):
    ctx = get_global_context(request)
    scenarios = Scenario.objects.all()
    
    if request.method == 'POST':
        code = request.POST.get('code')
        title = request.POST.get('title')
        cat = request.POST.get('category')
        sev = request.POST.get('severity')
        desc = request.POST.get('description')
        injects = request.POST.get('inject_timeline')
        impact = request.POST.get('expected_impact')
        mit = request.POST.get('recommended_mitigation')
        
        scn = Scenario.objects.create(
            code=code, title=title, category=cat, severity=sev,
            description=desc, inject_timeline=injects,
            expected_impact=impact, recommended_mitigation=mit,
            is_approved=True
        )
        AuditLogEntry.objects.create(
            user='Resilience Architect', action='Added Scenario',
            entity_type='Scenario', entity_id=scn.code,
            details=f"Cataloged exercise scenario {scn.title} under {scn.category}."
        )
        messages.success(request, f"Scenario {scn.code} added to Scenario Library.")
        return redirect('scenarios_list')

    ctx.update({
        'scenarios': scenarios,
        'active_menu': 'scenarios'
    })
    return render(request, 'bcm_app/scenarios_list.html', ctx)


@login_required
def rtep_tests_view(request):
    ctx = get_global_context(request)
    tests = RTEPTestExercise.objects.select_related('scenario', 'target_service').all()
    scenarios = Scenario.objects.all()
    services = CriticalService.objects.all()
    
    if request.method == 'POST':
        code = request.POST.get('test_code')
        title = request.POST.get('title')
        scn_id = request.POST.get('scenario_id')
        svc_id = request.POST.get('service_id')
        ex_type = request.POST.get('exercise_type')
        date_str = request.POST.get('scheduled_date')
        facilitator = request.POST.get('lead_facilitator')
        target_rto = int(request.POST.get('target_rto_minutes', 60))
        
        scenario = get_object_or_404(Scenario, id=scn_id)
        service = get_object_or_404(CriticalService, id=svc_id)
        
        test = RTEPTestExercise.objects.create(
            test_code=code, title=title, scenario=scenario,
            target_service=service, exercise_type=ex_type,
            scheduled_date=date_str or timezone.now(),
            lead_facilitator=facilitator, status='Scheduled',
            target_rto_minutes=target_rto
        )
        AuditLogEntry.objects.create(
            user=facilitator, action='Scheduled Test Exercise',
            entity_type='RTEPTestExercise', entity_id=test.test_code,
            details=f"Scheduled {test.exercise_type} against {service.name}."
        )
        messages.success(request, f"Exercise {test.test_code} scheduled.")
        return redirect('rtep_tests')

    ctx.update({
        'tests': tests,
        'scenarios': scenarios,
        'services': services,
        'active_menu': 'rtep'
    })
    return render(request, 'bcm_app/rtep_tests.html', ctx)


@login_required
def rtep_live_drill_view(request, test_id):
    ctx = get_global_context(request)
    test = get_object_or_404(RTEPTestExercise, id=test_id)
    
    if request.method == 'POST':
        outcome = request.POST.get('outcome', 'Successful')
        actual_time = int(request.POST.get('actual_recovery_time_minutes', 45))
        log = request.POST.get('execution_log', '')
        obs = request.POST.get('key_observations', '')
        
        test.status = 'Completed'
        test.outcome = outcome
        test.actual_recovery_time_minutes = actual_time
        test.execution_log = log
        test.key_observations = obs
        test.save()
        
        AuditLogEntry.objects.create(
            user=test.lead_facilitator, action='Executed RTEP Exercise',
            entity_type='RTEPTestExercise', entity_id=test.test_code,
            details=f"Completed drill {test.title}. Outcome: {test.outcome}. Actual recovery: {test.actual_recovery_time_minutes}m."
        )
        messages.success(request, f"Drill {test.test_code} completed and logged.")
        return redirect('rtep_tests')

    ctx.update({
        'test': test,
        'active_menu': 'rtep'
    })
    return render(request, 'bcm_app/rtep_live_drill.html', ctx)


# ----------------- 7. Cascading Impact Engine & Simulation -----------------
@login_required
def impact_engine_view(request):
    ctx = get_global_context(request)
    services = CriticalService.objects.all()
    vendors = ICTThirdParty.objects.all()
    
    ctx.update({
        'services': services,
        'vendors': vendors,
        'active_menu': 'impact'
    })
    return render(request, 'bcm_app/impact_engine.html', ctx)


@login_required
@csrf_exempt
def api_impact_simulate(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
    except:
        data = request.POST
        
    target_type = data.get('target_type')  # 'service' or 'vendor'
    target_id = data.get('target_id')
    duration_hours = float(data.get('duration_hours', 2.0))
    
    direct_services = []
    cascading_services = []
    impacted_services_ids = set()
    total_hourly_loss = 0.0
    target_name = ""
    
    if target_type == 'vendor':
        vendor = get_object_or_404(ICTThirdParty, id=target_id)
        target_name = f"{vendor.name} ({vendor.service_provided})"
        # Services directly dependent on this vendor
        links = ServiceDependency.objects.filter(third_party=vendor)
        for link in links:
            s = link.source_service
            direct_services.append({
                'code': s.code, 'name': s.name, 'tier': s.tier,
                'rto': s.rto_hours, 'loss_per_hour': float(s.financial_loss_per_hour),
                'reason': f"Direct dependency on {vendor.name}"
            })
            impacted_services_ids.add(s.id)
            total_hourly_loss += float(s.financial_loss_per_hour)
    else:
        service = get_object_or_404(CriticalService, id=target_id)
        target_name = f"{service.code}: {service.name}"
        direct_services.append({
            'code': service.code, 'name': service.name, 'tier': service.tier,
            'rto': service.rto_hours, 'loss_per_hour': float(service.financial_loss_per_hour),
            'reason': "Root Point of Outage"
        })
        impacted_services_ids.add(service.id)
        total_hourly_loss += float(service.financial_loss_per_hour)

    # Cascading downstream pass (services that depend on the directly impacted services)
    # Notice: source_service -> dependent_service (source depends on dependent)
    # If dependent fails, source service is affected!
    for _ in range(2): # 2-level traversal
        newly_found = []
        for imp_id in list(impacted_services_ids):
            dependent_on_this = ServiceDependency.objects.filter(dependent_service_id=imp_id)
            for d in dependent_on_this:
                s = d.source_service
                if s.id not in impacted_services_ids:
                    cascading_services.append({
                        'code': s.code, 'name': s.name, 'tier': s.tier,
                        'rto': s.rto_hours, 'loss_per_hour': float(s.financial_loss_per_hour),
                        'reason': f"Cascading failure from upstream {d.dependent_service.name}"
                    })
                    impacted_services_ids.add(s.id)
                    total_hourly_loss += float(s.financial_loss_per_hour)
                    newly_found.append(s.id)

    total_projected_loss = total_hourly_loss * duration_hours
    rto_breaches = [s for s in direct_services + cascading_services if s['rto'] < duration_hours]

    # Generate contingency recommendations
    contingency_plans = []
    for s_code in [s['code'] for s in direct_services]:
        bcp = BCPlan.objects.filter(service__code=s_code).first()
        if bcp:
            contingency_plans.append({
                'code': bcp.plan_code,
                'title': bcp.title,
                'strategy': bcp.recovery_strategy,
                'dr_site': bcp.dr_site
            })

    result = {
        'target_name': target_name,
        'duration_hours': duration_hours,
        'direct_impact_count': len(direct_services),
        'cascading_impact_count': len(cascading_services),
        'total_impacted_count': len(direct_services) + len(cascading_services),
        'total_hourly_loss': total_hourly_loss,
        'total_projected_loss': total_projected_loss,
        'rto_breaches_count': len(rto_breaches),
        'direct_services': direct_services,
        'cascading_services': cascading_services,
        'rto_breaches': rto_breaches,
        'contingency_plans': contingency_plans
    }
    return JsonResponse(result)


# ----------------- 8. Findings & Remediation (CAPA) -----------------
@login_required
def findings_list_view(request):
    ctx = get_global_context(request)
    findings = Finding.objects.select_related('service', 'test_exercise').all()
    services = CriticalService.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            code = request.POST.get('finding_code')
            title = request.POST.get('title')
            svc_id = request.POST.get('service_id')
            sev = request.POST.get('severity')
            root = request.POST.get('root_cause')
            plan = request.POST.get('remediation_plan')
            assigned = request.POST.get('assigned_to')
            due = request.POST.get('due_date') or (date.today() + timedelta(days=30))
            
            service = get_object_or_404(CriticalService, id=svc_id)
            f = Finding.objects.create(
                finding_code=code, title=title, service=service,
                severity=sev, status='Open', root_cause=root,
                remediation_plan=plan, assigned_to=assigned, due_date=due
            )
            AuditLogEntry.objects.create(
                user='QA Auditor', action='Logged Finding',
                entity_type='Finding', entity_id=f.finding_code,
                details=f"Opened finding {f.title} ({f.severity}) for {service.name}."
            )
            messages.success(request, f"Finding {f.finding_code} registered.")
            
        elif action == 'update_status':
            f_id = request.POST.get('finding_id')
            new_status = request.POST.get('status')
            notes = request.POST.get('retest_notes', '')
            f = get_object_or_404(Finding, id=f_id)
            f.status = new_status
            f.retest_notes = notes
            f.save()
            messages.success(request, f"Finding {f.finding_code} status updated to {new_status}.")
            
        return redirect('findings_list')

    ctx.update({
        'findings': findings,
        'services': services,
        'active_menu': 'findings'
    })
    return render(request, 'bcm_app/findings_list.html', ctx)


# ----------------- 9. Evidence Repository -----------------
@login_required
def evidence_repository_view(request):
    ctx = get_global_context(request)
    evidence_items = EvidenceItem.objects.select_related('service', 'test_exercise').all()
    services = CriticalService.objects.all()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        etype = request.POST.get('evidence_type')
        svc_id = request.POST.get('service_id')
        fname = request.POST.get('file_name', 'compliance_proof.pdf')
        size = int(request.POST.get('file_size_kb', 1024))
        uploaded_by = request.POST.get('uploaded_by', 'Auditor')
        
        service = CriticalService.objects.filter(id=svc_id).first() if svc_id else None
        item = EvidenceItem.objects.create(
            title=title, evidence_type=etype, service=service,
            file_name=fname, file_size_kb=size, uploaded_by=uploaded_by
        )
        AuditLogEntry.objects.create(
            user=uploaded_by, action='Uploaded Evidence',
            entity_type='EvidenceItem', entity_id=str(item.id),
            details=f"Uploaded {item.file_name} for audit repository."
        )
        messages.success(request, f"Evidence item '{item.title}' cataloged.")
        return redirect('evidence_repository')

    ctx.update({
        'evidence_items': evidence_items,
        'services': services,
        'active_menu': 'evidence'
    })
    return render(request, 'bcm_app/evidence_repository.html', ctx)


# ----------------- 10. Approvals & Workflows Queue -----------------
@login_required
def approval_queue_view(request):
    ctx = get_global_context(request)
    tasks = ApprovalTask.objects.all()
    
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        action = request.POST.get('action') # 'approve', 'reject', 'delegate'
        comments = request.POST.get('comments', '')
        
        task = get_object_or_404(ApprovalTask, id=task_id)
        if action == 'approve':
            task.status = 'Approved'
        elif action == 'reject':
            task.status = 'Rejected'
        elif action == 'delegate':
            task.status = 'Delegated'
            task.assigned_to = request.POST.get('delegate_to', 'Deputy Officer')
            
        task.comments = (task.comments + "\n" + comments).strip()
        task.actioned_date = timezone.now()
        task.save()
        
        AuditLogEntry.objects.create(
            user='Authorizing Official', action=f"{task.status} Task",
            entity_type='ApprovalTask', entity_id=task.task_code,
            details=f"Status set to {task.status}. Notes: {comments}"
        )
        messages.success(request, f"Task {task.task_code} marked as {task.status}.")
        return redirect('approval_queue')

    ctx.update({
        'tasks': tasks,
        'active_menu': 'approvals'
    })
    return render(request, 'bcm_app/approval_queue.html', ctx)


# ----------------- 11. ResQ AI Assistant -----------------
@login_required
def resq_ai_view(request):
    ctx = get_global_context(request)
    chat_history = ResQChatLog.objects.all()[:15]
    
    ctx.update({
        'chat_history': chat_history,
        'active_menu': 'resq'
    })
    return render(request, 'bcm_app/resq_ai.html', ctx)


@login_required
@csrf_exempt
def api_resq_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
        
    try:
        data = json.loads(request.body)
    except:
        data = request.POST
        
    query = data.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'Empty query'}, status=400)
        
    q_lower = query.lower()
    
    # Context-aware intelligent BCM reasoning engine
    matched_services = []
    
    if 'aws' in q_lower or 'cloud' in q_lower or 'datacenter' in q_lower or 'frankfurt' in q_lower:
        aws_vendor = ICTThirdParty.objects.filter(vendor_code__icontains='AWS').first()
        deps = ServiceDependency.objects.filter(third_party__vendor_code__icontains='AWS')
        direct_svcs = [d.source_service for d in deps]
        matched_services = [s.code for s in direct_svcs]
        
        reply = (
            f"**Impact Assessment for Cloud Infrastructure:**\n\n"
            f"• Directly linked services: **{', '.join([s.name + ' (' + s.code + ')' for s in direct_svcs]) if direct_svcs else 'Payment Gateway & Containers'}**\n"
            f"• Recovery Objective: Target RTO is **1.0 hour**, RPO **0.0 hours**.\n"
            f"• Primary Disaster Strategy: Automatic cross-region cutover from Frankfurt `eu-central-1` to Dublin `eu-west-1` warm standby.\n"
            f"• Contingency Action: Execute Runbook **BCP-PAY-2027** step 3 (Promote Ireland Aurora replica and re-route Cloudflare Anycast traffic)."
        )
    elif 'rto' in q_lower or 'tier 1' in q_lower or 'critical' in q_lower or 'hours' in q_lower:
        t1 = CriticalService.objects.filter(tier='Tier 1')
        matched_services = [s.code for s in t1]
        lines = [f"• **{s.code}: {s.name}** — RTO: `{s.rto_hours}h`, RPO: `{s.rpo_hours}h`, MTPD: `{s.mtpd_hours}h`, Hourly Exposure: `${s.financial_loss_per_hour:,.0f}`" for s in t1]
        reply = (
            f"**Tier 1 Mission-Critical Services Overview:**\n\n"
            + "\n".join(lines) +
            f"\n\n*All {t1.count()} Tier 1 services currently have active Business Continuity Plans approved.*"
        )
    elif 'finding' in q_lower or 'capa' in q_lower or 'remediation' in q_lower or 'vulnerability' in q_lower:
        open_f = Finding.objects.exclude(status='Closed & Verified')
        lines = [f"• **{f.finding_code}** [{f.severity}]: {f.title} (Assigned to {f.assigned_to}, Due: {f.due_date})" for f in open_f[:4]]
        reply = (
            f"**Current Open BCM Findings ({open_f.count()} active):**\n\n"
            + "\n".join(lines) +
            f"\n\nRecommendation: Prioritize **FND-8802** (Core Banking Lock Eviction) currently pending retest approval."
        )
    elif 'dora' in q_lower or 'compliance' in q_lower or 'iso 22301' in q_lower:
        total_v = ICTThirdParty.objects.count()
        dora_v = ICTThirdParty.objects.filter(dora_compliant=True).count()
        reply = (
            f"**Regulatory & DORA Compliance Status:**\n\n"
            f"• **ICT Third-Party Register**: {dora_v}/{total_v} registered critical vendors verified for EU DORA Article 28 compliance.\n"
            f"• **BIA Attestation**: 85.7% of critical services have attested BIAs within the last 365 days (ISO 22301 Clause 8.2.2 requirement).\n"
            f"• **RTEP Testing**: 100% of Tier 1 services have scheduled or completed resilience testing for Q1/Q2."
        )
    else:
        # Generic intelligent response
        total_s = CriticalService.objects.count()
        total_b = BCPlan.objects.count()
        reply = (
            f"I have analyzed your BCM enterprise repository containing **{total_s} registered critical services** and **{total_b} active continuity plans**.\n\n"
            f"How can I assist you further? You can ask me:\n"
            f"1. *'What happens if AWS Frankfurt fails?'*\n"
            f"2. *'Show all Tier 1 services with RTO under 2 hours'*\n"
            f"3. *'List open critical findings and remediation progress'*\n"
            f"4. *'Summary of DORA compliance readiness'*"
        )

    # Save to history
    log = ResQChatLog.objects.create(
        user_query=query,
        ai_response=reply,
        matched_services=",".join(matched_services),
        feedback_positive=True
    )
    
    return JsonResponse({
        'reply': reply,
        'matched_services': matched_services,
        'log_id': log.id
    })


# ----------------- 12. Administration & Audit Log -----------------
@login_required
def admin_audit_view(request):
    ctx = get_global_context(request)
    audit_logs = AuditLogEntry.objects.all()[:50]
    total_logs = AuditLogEntry.objects.count()
    
    ctx.update({
        'audit_logs': audit_logs,
        'total_logs': total_logs,
        'active_menu': 'admin'
    })
    return render(request, 'bcm_app/admin_audit.html', ctx)


# ----------------- 13. Role Management & User Administration (Milestone 1, APIs 109-111, 119-120) -----------------
@login_required
def roles_management_view(request):
    ctx = get_global_context(request)
    roles = RoleDefinition.objects.prefetch_related('members').all()
    users = User.objects.select_related('profile', 'profile__role_def').all().order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Assign role to user (API 110: PUT /admin/users)
        if action == 'assign_user_role':
            user_id = request.POST.get('user_id')
            role_id = request.POST.get('role_id')
            target_user = get_object_or_404(User, id=user_id)
            target_role = get_object_or_404(RoleDefinition, id=role_id)

            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            old_role = profile.role
            profile.role_def = target_role
            profile.role = target_role.name
            profile.avatar_color = target_role.color
            profile.save()

            AuditLogEntry.objects.create(
                user=request.user.get_full_name() or request.user.username,
                action='Updated User Role',
                entity_type='User',
                entity_id=target_user.username,
                details=f"Changed assigned role from '{old_role}' to '{target_role.name}'.",
                ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
            )
            messages.success(request, f"Updated role for {target_user.get_full_name() or target_user.username} to '{target_role.name}'.")
            return redirect('roles_management')

        # 2. Update role permissions (API 120: PUT /admin/permissions)
        elif action == 'update_role_permissions':
            role_id = request.POST.get('role_id')
            role_obj = get_object_or_404(RoleDefinition, id=role_id)

            role_obj.can_attest_bia = bool(request.POST.get('can_attest_bia'))
            role_obj.can_approve_bcp = bool(request.POST.get('can_approve_bcp'))
            role_obj.can_execute_drills = bool(request.POST.get('can_execute_drills'))
            role_obj.can_manage_third_parties = bool(request.POST.get('can_manage_third_parties'))
            role_obj.can_close_findings = bool(request.POST.get('can_close_findings'))
            role_obj.can_manage_roles_users = bool(request.POST.get('can_manage_roles_users'))
            role_obj.can_view_audit_logs = bool(request.POST.get('can_view_audit_logs'))
            role_obj.save()

            AuditLogEntry.objects.create(
                user=request.user.get_full_name() or request.user.username,
                action='Updated Role Permissions',
                entity_type='RoleDefinition',
                entity_id=role_obj.code,
                details=f"Modified permission matrix for {role_obj.name}.",
                ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
            )
            messages.success(request, f"Permissions updated for role '{role_obj.name}'.")
            return redirect('roles_management')

        # 3. Create new custom role (API 111: POST /admin/roles)
        elif action == 'create_role':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            desc = request.POST.get('description', '').strip()
            color = request.POST.get('color', '#6366f1')

            if not code.startswith('ROLE_'):
                code = f"ROLE_{code}"

            r_obj = RoleDefinition.objects.create(
                name=name, code=code, description=desc, color=color,
                can_attest_bia=bool(request.POST.get('can_attest_bia')),
                can_approve_bcp=bool(request.POST.get('can_approve_bcp')),
                can_execute_drills=bool(request.POST.get('can_execute_drills')),
                can_manage_third_parties=bool(request.POST.get('can_manage_third_parties')),
                can_close_findings=bool(request.POST.get('can_close_findings')),
                can_manage_roles_users=bool(request.POST.get('can_manage_roles_users')),
                can_view_audit_logs=bool(request.POST.get('can_view_audit_logs')),
                is_system_role=False,
            )
            AuditLogEntry.objects.create(
                user=request.user.get_full_name() or request.user.username,
                action='Created Custom Role',
                entity_type='RoleDefinition',
                entity_id=r_obj.code,
                details=f"Provisioned custom role '{r_obj.name}'.",
                ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
            )
            messages.success(request, f"Custom role '{r_obj.name}' successfully created.")
            return redirect('roles_management')

        # 4. Provision new user (API 109/110)
        elif action == 'create_user':
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip() or 'bcmpassword123'
            role_id = request.POST.get('role_id')
            dept = request.POST.get('department', '').strip()
            phone = request.POST.get('phone', '').strip()

            target_role = get_object_or_404(RoleDefinition, id=role_id)
            new_u = User.objects.create_user(
                username=username, first_name=first_name, last_name=last_name, email=email, password=password
            )
            UserProfile.objects.create(
                user=new_u,
                role_def=target_role,
                role=target_role.name,
                department=dept or 'Operational Resilience',
                phone=phone or '+44 20 7946 0890',
                sso_id=f"OKTA-{username.upper()}-01",
                avatar_color=target_role.color
            )
            AuditLogEntry.objects.create(
                user=request.user.get_full_name() or request.user.username,
                action='Provisioned Enterprise User',
                entity_type='User',
                entity_id=new_u.username,
                details=f"Provisioned user '{new_u.username}' with role '{target_role.name}'.",
                ip_address=request.META.get('REMOTE_ADDR', '10.24.8.102')
            )
            messages.success(request, f"Provisioned enterprise user '{new_u.username}' with role '{target_role.name}'.")
            return redirect('roles_management')

    ctx.update({
        'roles': roles,
        'users': users,
        'active_menu': 'roles',
    })
    return render(request, 'bcm_app/roles_management.html', ctx)

