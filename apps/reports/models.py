# apps/reports/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# 1. Report Category
class ReportCategory(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

# 2. Report Definition (The Brain)
class ReportDefinition(models.Model):
    category = models.ForeignKey(ReportCategory, on_delete=models.PROTECT)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()

    data_sources = models.JSONField(help_text="Definition of data extraction logic")
    filters_schema = models.JSONField(help_text="JSON Schema for allowed parameters")
    output_formats = models.JSONField(default=list, help_text="['pdf', 'xlsx', 'csv']")

    is_active = models.BooleanField(default=True)
    is_sensitive = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.code})"

# 3. Report Execution (Audit Trail)
class ReportExecution(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    report_definition = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    parameters = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.report_definition.code} by {self.executed_by} at {self.started_at}"

# 4. Report Artifact (The File)
class ReportArtifact(models.Model):
    execution = models.ForeignKey(ReportExecution, on_delete=models.CASCADE, related_name='artifacts')
    file = models.FileField(upload_to='reports/%Y/%m/')
    format = models.CharField(max_length=10)  # pdf, csv, xlsx
    checksum = models.CharField(max_length=64, blank=True, help_text="SHA2-256 for integrity compliance")
    is_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.execution} [{self.format}]"

# 5. Report Permission (Access Control)
class ReportPermission(models.Model):
    report_definition = models.ForeignKey(ReportDefinition, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, help_text="Role code allowed to access this report")
    
    def __str__(self):
        return f"{self.role} -> {self.report_definition}"

# 6. KPI (Key Performance Indicator)
class KPI(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField()

    formula = models.TextField(help_text="Logic or SQL description for calculation")
    target_value = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return self.name

# 7. KPI Result (Historical Data)
class KPIResult(models.Model):
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE)
    period = models.CharField(max_length=20, help_text="Ex: 2024-Q1, 2025-JAN")
    value = models.FloatField()
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.kpi.code} [{self.period}] = {self.value}"

# 8. Accreditation Report (Compliance)
class AccreditationReport(models.Model):
    authority = models.CharField(max_length=200, help_text="Ex: Ministério da Educação, Board of Regents")
    academic_year = models.ForeignKey('academic.AcademicYear', on_delete=models.CASCADE)

    generated_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='accreditation/')
    
    def __str__(self):
        return f"{self.authority} ({self.academic_year})"
