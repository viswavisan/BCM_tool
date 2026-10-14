from django.urls import path
from . import views

urlpatterns = [
    # Dashboards
    path('', views.dashboard_view, name='dashboard'),
    
    # Critical Services Registry
    path('services/', views.services_list_view, name='services_list'),
    path('services/<int:service_id>/', views.service_detail_view, name='service_detail'),
    path('ict-third-parties/', views.ict_third_party_view, name='ict_third_party'),
    
    # BIA
    path('bia/', views.bia_list_view, name='bia_list'),
    path('bia/<int:bia_id>/', views.bia_detail_view, name='bia_detail'),
    path('bia/<int:bia_id>/attest/', views.bia_attest_view, name='bia_attest'),
    
    # Dependencies & Lineage
    path('dependencies/', views.dependencies_graph_view, name='dependencies_graph'),
    path('api/dependencies/graph/', views.api_dependencies_graph, name='api_dependencies_graph'),
    
    # BC Plans
    path('bcp/', views.bcp_list_view, name='bcp_list'),
    path('bcp/<int:bcp_id>/', views.bcp_detail_view, name='bcp_detail'),
    
    # Scenarios & RTEP Testing
    path('scenarios/', views.scenarios_list_view, name='scenarios_list'),
    path('rtep/', views.rtep_tests_view, name='rtep_tests'),
    path('rtep/<int:test_id>/drill/', views.rtep_live_drill_view, name='rtep_live_drill'),
    
    # Impact Engine & Simulation
    path('impact/', views.impact_engine_view, name='impact_engine'),
    path('api/impact/simulate/', views.api_impact_simulate, name='api_impact_simulate'),
    
    # Findings & Remediation (CAPA)
    path('findings/', views.findings_list_view, name='findings_list'),
    
    # Evidence Repository
    path('evidence/', views.evidence_repository_view, name='evidence_repository'),
    
    # Workflow & Approvals
    path('approvals/', views.approval_queue_view, name='approval_queue'),
    
    # ResQ AI
    path('resq/', views.resq_ai_view, name='resq_ai'),
    path('api/resq/chat/', views.api_resq_chat, name='api_resq_chat'),
    
    # Admin & Audit
    path('admin-audit/', views.admin_audit_view, name='admin_audit'),
]
