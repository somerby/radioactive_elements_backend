from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.contrib.auth.models import Group, Permission

class NewUserManager(UserManager):
    def create_user(self,email,password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')
        
        email = self.normalize_email(email) 
        user = self.model(email=email, **extra_fields) 
        user.set_password(password)
        user.save(using=self.db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(("email адрес"), unique=True)
    password = models.CharField(max_length=50, verbose_name="Пароль")    
    is_staff = models.BooleanField(default=False, verbose_name="Является ли пользователь менеджером?")
    is_superuser = models.BooleanField(default=False, verbose_name="Является ли пользователь админом?")

    USERNAME_FIELD = 'email'

    objects =  NewUserManager()
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_groups',  # Unique related_name to avoid clashes
        blank=True,
        verbose_name='Группы'
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_permissions',  # Unique related_name to avoid clashes
        blank=True,
        verbose_name='Разрешения'
    )

class Element(models.Model):
    status_choices = [
        ('active', 'действует'),
        ('deleted', 'удален')
    ]

    element_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=status_choices)
    img_url = models.CharField(max_length=100, null=True, blank=True)
    period_time_text = models.CharField(max_length=100)
    period_time = models.FloatField(default=0)
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

class Element_Decay(models.Model):
    element = models.ForeignKey(Element, on_delete=models.DO_NOTHING, related_name='element_decays')
    decay = models.ForeignKey(Decay, on_delete=models.DO_NOTHING, related_name='decay_elements')
    quantity = models.CharField(max_length=30, null=True, blank=True)
    remaining_quantity = models.CharField(max_length=40, null=True, blank=True)
    class Meta:
        unique_together = ('element', 'decay')