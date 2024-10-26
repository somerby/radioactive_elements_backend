from django.db import models
from django.contrib.auth import get_user_model

class Element(models.Model):
    element_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    description = models.TextField()
    status = models.CharField(max_length=20)
    img_url = models.CharField(max_length=100, null=True, blank=True)
    period_time_text = models.CharField(max_length=100)
    atomic_mass = models.IntegerField()

class Decay(models.Model):
    status_choices = [
        ('draft', 'черновик'),
        ('deleted', 'удален'),
        ('completed', 'завершен'),
        ('formed', 'сформирован'),
        ('rejected', 'отклонен')
    ]

    decay_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=status_choices)
    date_of_creation = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, related_name='user_decays')
    date_of_formation = models.DateTimeField(null=True, blank=True)
    date_of_finish = models.DateTimeField(null=True, blank=True)
    pass_time = models.CharField(max_length=30, null=True, blank=True)
    moderator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, related_name='moderator_decays', null=True, blank=True)
    remaining_quantity = models.CharField(max_length=40, null=True, blank=True)

class Element_Decay(models.Model):
    element_id = models.ForeignKey(Element, on_delete=models.DO_NOTHING, related_name='element_decays')
    decay_id = models.ForeignKey(Decay, on_delete=models.DO_NOTHING, related_name='decay_elements')
    quantity = models.CharField(max_length=30, null=True, blank=True)
    class Meta:
        unique_together = ('element_id', 'decay_id')