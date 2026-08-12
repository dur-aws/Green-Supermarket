from django.db import models

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    category_name = models.CharField(max_length=100)
    requires_expiry_tracking = models.BooleanField(blank=True, null=True)
    requires_batch_tracking = models.BooleanField(blank=True, null=True)
    requires_catch_weight = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'
        
    def __str__(self):
        return self.category_name
    