from django.db import models


class UnitOfMeasure(models.Model):
    uom_id = models.AutoField(primary_key=True)
    unit_name = models.CharField(unique=True, max_length=50)
    notation = models.CharField(max_length=10)
    is_weight_based = models.BooleanField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        managed = False
        db_table = 'unit_of_measure'
