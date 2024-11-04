from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import *
from .serializers import *
from .minio import deleteImg, addImg

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

import re
import math

UNIT_CONVERSIONS = {
            'кг': 1000,
            'килограмм': 1000,
            'килограммов': 1000,
            'г': 1,
            'грамм': 1,
            'граммов': 1,
            'мг': 0.001,
            'миллиграмм': 0.001,
            'миллиграммов': 0.001,
            'мкг': 0.000001,
            'микрограмм': 0.000001,
            'микрограммов': 0.000001,
            'мкс': 0.000001,
            'микросекунд': 0.000001,
            'микросекунда': 0.000001,
            'мс': 0.000001,
            'миллисекунд': 0.000001,
            'миллисекунда': 0.000001,
            'с': 0.000001,
            'секунд': 0.000001,
            'секунда': 0.000001,
            'м': 60,
            'минут': 60,
            'минута': 60,
            'ч': 3600,
            'час': 3600,
            'часа': 3600,
            'часов': 3600,
            'д': 86400,
            'день': 86400,
            'дней': 86400,
            'дня': 86400,
            'н': 604800,
            'неделя': 604800,
            'недели': 604800,
            'недель': 604800,
            'мес': 2678400,
            'месяц': 2678400,
            'месяца': 2678400,
            'месяцев': 2678400,
            'г': 31536000,
            'год': 31536000,
            'года': 31536000,
            'лет': 31536000,
        }

def getDecayInformation(user):
    decay = user.user_decays.all().filter(status='draft').first()
    if decay is None:
        decay_elements_count = 0 
        decay_id = 0
    else:
        decay_elements_count = Element_Decay.objects.filter(decay_id=decay.decay_id).count()
        decay_id = decay.decay_id

    return {'decay_elements_count': decay_elements_count, 
            'decay_id': decay_id}

def curr_user():
    return get_user_model().objects.get(id = 1)

def unit_parse(text):
    match = re.match(r'(\d+[.,]?\d*)\s*(\D+)', text)
    if not match:
        raise NameError()
    value = float(match.group(1).replace(',', '.'))
    unit = match.group(2).strip().lower()
    if unit in UNIT_CONVERSIONS:
        return value * UNIT_CONVERSIONS[unit]
    else:
        raise ValueError()

def half_life_calculation(pass_time_text, quantity_text, period_time):
    pass_time = unit_parse(pass_time_text)
    quantity = unit_parse(quantity_text)
    lambda_decay = math.log(2) / period_time
    remaining_mass = quantity * math.exp(-lambda_decay * pass_time)
    return remaining_mass

class elementsMethods(APIView):
    serializer = ElementSerializer

    def get(self, request):
        search_number = request.query_params.get('atomic_mass', '')
        elements = Element.objects.filter(atomic_mass__contains=search_number)
        decay_information = getDecayInformation(curr_user())
        serial_data = self.serializer(elements, many = True)
        return Response({'search_number': search_number, 
                         'elements': serial_data.data, 
                         'decay_information': decay_information},
                         status=status.HTTP_200_OK)
    def post(self, request):
        input_data = self.serializer(data=request.data)
        if input_data.is_valid():
            input_data.save()
            return Response(input_data.data, status=status.HTTP_201_CREATED)
        return Response(input_data.errors, status=status.HTTP_400_BAD_REQUEST)

class elementMethods(APIView):
    serializer = ElementSerializer

    def get(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        return Response(self.serializer(element).data, status=status.HTTP_200_OK)
    def post(self, request, element_id):
        decay, is_created = Decay.objects.get_or_create(
            creator = curr_user(),
            status = 'draft',
        )
        if Element_Decay.objects.filter(element=element_id, decay=decay.decay_id).exists():
            return Response(status=status.HTTP_208_ALREADY_REPORTED)
        else:
            Element_Decay.objects.create(
                decay = Decay.objects.get(decay_id=decay.decay_id),
                element = Element.objects.get(element_id=element_id)
            )
            return Response(status=status.HTTP_200_OK)
    def put(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        changed_element = self.serializer(element, request.data, partial=True)
        if changed_element.is_valid():
            changed_element.save()
            return Response(changed_element.data, status=status.HTTP_200_OK)
        return Response(changed_element.errors, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        if element.status != 'deleted':
            element.status = 'deleted'
            if deleteImg(element.img_url) == 'success':
                element.img_url = ''
                element.save()
                return Response(self.serializer(element).data, status=status.HTTP_204_NO_CONTENT)
            element.save()
            return Response({'s3_img': 'Удаление не удалось'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'element', 'Элемент уже удален'}, status=status.HTTP_208_ALREADY_REPORTED)

@api_view(['post'])
def elementAddImg(request, element_id):
    element = get_object_or_404(Element, element_id=element_id)
    img = request.FILES.get('img')
    try:
        element.img_url = addImg(img)
        element.save()
        return Response(ElementSerializer(element).data, status=status.HTTP_202_ACCEPTED)
    except:
        return Response({'img': 'Ошибка загрузки'}, status=status.HTTP_400_BAD_REQUEST)


class elementDecayMethods(APIView):
    serializer = ElementDecaySerializer

    def delete(self, request, element_id, decay_id):
        element_decay = get_object_or_404(Element_Decay, element=element_id, decay=decay_id)
        element_decay.delete()
        elements_decay = Element_Decay.objects.filter(decay=decay_id)
        return Response(self.serializer(elements_decay, many=True).data, status=status.HTTP_200_OK)
    def put(self, request, element_id, decay_id):
        element_decay = get_object_or_404(Element_Decay, element=element_id, decay=decay_id)
        changed_element_decay = self.serializer(element_decay, data=request.data, partial=True) 
        if changed_element_decay.is_valid():
            changed_element_decay.save() 
            elements_decay = Element_Decay.objects.filter(decay=decay_id)
            return Response(self.serializer(elements_decay, many=True).data, status=status.HTTP_200_OK)
        return Response(changed_element_decay.errors, status=status.HTTP_400_BAD_REQUEST)

class decaysMethods(APIView):
    serializer = DecaySerializer

    def get(self, request):
        acceptable_statuses = [
            'completed',
            'formed',
            'rejected'
        ]

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        decays = Decay.objects.filter(status__in=acceptable_statuses)

        if start_date and end_date:
            start_date = parse_date(start_date)
            end_date = parse_date(end_date)
            if start_date is None or end_date is None:
                return Response({'error': 'Неправильный формат даты'}, status=status.HTTP_400_BAD_REQUEST)
            decays = decays.filter(date_of_creation__range=(start_date, end_date))

        if status_filter:
            if not status_filter in acceptable_statuses:
                return Response({'error': 'Неправильный статус'}, status=status.HTTP_400_BAD_REQUEST)
            decays = decays.filter(status=status_filter)
        return Response(self.serializer(decays, many=True).data, status=status.HTTP_200_OK)
    
class decayMethods(APIView):
    serializer = DecaySerializer

    def get(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        return Response(self.serializer(decay).data, status=status.HTTP_200_OK)
    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        changed_decay = self.serializer(decay, data=request.data, partial=True)
        if changed_decay.is_valid():
            changed_decay.save()
            return Response(changed_decay.data, status=status.HTTP_200_OK)
        return Response(changed_decay.errors, status=status.HTTP_400_BAD_REQUEST)

class formingDecay(APIView):
    serializer = DecaySerializer

    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        elements = decay.decay_elements.all()
        if decay.status == 'draft':
            if not decay.pass_time is None and decay.pass_time != '':
                for element in elements:
                    if element.quantity is None or element.quantity == '':
                        return Response({'quantity': 'Не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
                decay.status = 'formed'
                decay.date_of_formation = timezone.now()
                decay.save()
                return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({'pass_time': 'Не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'status': 'Должен быть черновик'}, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        if decay.status == 'draft':
            decay.status = 'deleted'
            decay.date_of_formation = timezone.now()
            decay.save()
            return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'decay': 'Заявка - не черновик'}, status=status.HTTP_400_BAD_REQUEST)

class moderateDecay(APIView):
    serializer = DecaySerializer

    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        action = request.data.get('action')
        if curr_user().is_superuser:
            if decay.status == 'formed':
                if action == 'reject':
                    decay.status = 'rejected'
                    decay.moderator = curr_user()
                    decay.date_of_finish = timezone.now()
                    decay.save()
                    return Response(self.serializer(decay).data, status=status.HTTP_200_OK)
                elif action == 'complete':
                    elements = decay.decay_elements.all()
                    for element in elements:
                        try:
                            element.remaining_quantity = str(half_life_calculation(decay.pass_time, element.quantity, element.element.period_time)) + ' грамм'
                        except NameError:
                            element.remaining_quantity = 'Неверный формат входных данных'
                        except ValueError:
                            element.remaining_quantity = 'Неверный формат единиц измерения'
                        element.save()
                    decay.moderator = curr_user()
                    decay.status = 'completed'
                    decay.date_of_finish = timezone.now()
                    decay.save()
                    return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({'action': 'Неверное действие'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'status': 'Заявка - не сформирована'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'user': 'Нет доступа!'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['post'])
def userRegistration(request):
    ser_data = UserSerializer(data=request.data)
    if ser_data.is_valid():
        user = get_user_model().objects.create_user(
            username = ser_data.validated_data.get('username'),
            password = ser_data.validated_data.get('password'),
            is_superuser = ser_data.validated_data.get('is_superuser'),
            is_staff = ser_data.validated_data.get('is_staff'),
            email = ser_data.validated_data.get('email'),
            first_name = ser_data.validated_data.get('first_name'),
            last_name = ser_data.validated_data.get('last_name')
        )
        users = get_user_model().objects.all()
        return Response(UserSerializer(users, many=True).data, status=status.HTTP_201_CREATED)
    return Response(ser_data.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['put'])
def userAccount(request, username):
    user = get_object_or_404(get_user_model(), username=username)
    ser_data = UserSerializer(user, data=request.data, partial=True)
    if ser_data.is_valid():
        ser_data.save()
        if 'password' in ser_data.validated_data:
            user.set_password(ser_data.validated_data.get('password'))
            user.save()
        return Response(ser_data.data, status=status.HTTP_202_ACCEPTED)
    return Response(ser_data.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['post'])
def userAuthentication(request):
    user = get_object_or_404(get_user_model(), username=request.data.get('username'))
    if user.check_password(request.data.get('password')):
        return Response({'user': request.data.get('username'), 'auth': 'Выполнен вход'}, status=status.HTTP_200_OK)
    return Response({'user': request.data.get('username'), 'auth': 'Неверно введенные данные'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['post'])
def userDeauthentication(request):
    return Response({'user': request.data.get('username'), 'deauth': 'Выполнен выход'})