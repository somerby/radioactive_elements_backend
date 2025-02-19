from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.contrib.auth import authenticate, logout
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q

from .models import *
from .serializers import *
from .minio import deleteImg, addImg
from .hl_calc import HalfLifeCalculation
from .permissions import IsManager, IsAdmin, AuthBySSID, IsAuth
from .redis import session_storage

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import uuid

from .qr_generate import generate_decay_qr

error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'details': openapi.Schema(type=openapi.TYPE_STRING)
    },
    required=['details']
)

ok_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'status': openapi.Schema(type=openapi.TYPE_STRING)
    },
    required=['status']
)

def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes        
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator

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

@csrf_exempt
@swagger_auto_schema(method='post', 
                     request_body=SwaggerCustomUserSerializer,
                     responses={
                        200: openapi.Response(
                            description='Успешная аутентификация',
                            schema=CustomUserSerializer
                        ),
                        400: openapi.Response(
                            description='Ошибка входа',
                            schema=error_schema
                        )
})
@api_view(['post'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data["email"] 
    password = request.data["password"]
    user = authenticate(request, email=username, password=password)
    if user is not None:
        random_key = str(uuid.uuid4())
        session_storage.set(random_key, username)

        response = Response(CustomUserSerializer(user).data, status=status.HTTP_200_OK)
        response.set_cookie("session_id", random_key)

        return response
    else:
        return Response({'details': 'login failed'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@swagger_auto_schema(method='post', 
                     request_body=None,
                     responses={
                        200: openapi.Response(
                            description='Успешный выход из системы',
                            schema=ok_schema
                        ),
                        400: openapi.Response(
                            description='Ошибка выхода из системы',
                            schema=error_schema
                        ),
                        403: openapi.Response(
                            description='Нет доступа',
                            schema=error_schema
                         )
})
@api_view(['post'])
@authentication_classes([AuthBySSID])
@permission_classes([IsAuth])
def logout_view(request):
    ssid = request.COOKIES.get("session_id")
    try:
        session_storage.delete(ssid)
        logout(request)
        return Response({'status': 'logged out'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'details': 'logout failed'}, status=status.HTTP_400_BAD_REQUEST)

class elementsMethods(APIView):
    serializer = ElementSerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(manual_parameters=[
                            openapi.Parameter(
                                name = 'atomic_mass',
                                in_ = openapi.IN_QUERY,
                                description='Атомная масса',
                                type=openapi.TYPE_STRING,
                                required=False
                            ),
                         ],
                         responses={
                            200: openapi.Response(
                                description='Элементы с номером черновой заявки и количеством в корзине',
                                schema=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'atomic_mass': openapi.Schema(type=openapi.TYPE_STRING),
                                        'elements': openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                                 properties={
                                                                     'element_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                                     'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                                     'description': openapi.Schema(type=openapi.TYPE_STRING),
                                                                     'status': openapi.Schema(type=openapi.TYPE_STRING),
                                                                     'img_url': openapi.Schema(type=openapi.TYPE_STRING),
                                                                     'period_time_text': openapi.Schema(type=openapi.TYPE_STRING),
                                                                     'period_time': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                                     'atomic_mass': openapi.Schema(type=openapi.TYPE_INTEGER)
                                                                 },
                                                                 required=['element_id', 
                                                                           'name', 
                                                                           'description', 
                                                                           'status', 
                                                                           'img_url', 
                                                                           'period_time_text', 
                                                                           'period_time', 
                                                                           'atomic_mass',
                                                                 ])
                                        ),
                                        'decay_information': openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'decay_elements_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'decay_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                                            },
                                            required=['decay_elements_count', 'decay_id']
                                        )
                                    },
                                    required=['atomic_mass', 'elements', 'decay_information']
                                )
                            )
    })
    @method_permission_classes([AllowAny])
    def get(self, request):
        atomic_mass = request.query_params.get('atomic_mass', '')
        elements = Element.objects.filter(atomic_mass__contains=atomic_mass)
        if request.user.is_authenticated:
            decay_information = getDecayInformation(request.user)
        else:
            decay_information = {'decay_elements_count': 0, 
                                 'decay_id': 0}
        serial_data = self.serializer(elements, many = True)
        return Response({'atomic_mass': atomic_mass, 
                         'elements': serial_data.data, 
                         'decay_information': decay_information},
                         status=status.HTTP_200_OK)
    
    @swagger_auto_schema(request_body=serializer,
                         responses={
                            201: openapi.Response(
                                description='Успешное создание элемента',
                                schema=ElementSerializer
                            ),
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            )
    })
    @method_permission_classes([IsManager])
    def post(self, request):
        input_data = self.serializer(data=request.data)
        if input_data.is_valid():
            input_data.save()
            return Response(input_data.data, status=status.HTTP_201_CREATED)
        return Response(input_data.errors, status=status.HTTP_400_BAD_REQUEST)

class elementMethods(APIView):
    serializer = ElementSerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(responses={
                            200: openapi.Response(
                                description='Успешное получение 1 элемента',
                                schema=ElementSerializer
                            ),
                            404: openapi.Response(
                                description='Не нашли элемент с таким id',
                                schema=error_schema
                            )
    })
    @method_permission_classes([AllowAny])
    def get(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        if element.status == 'deleted':
            if request.user.is_anonymous:
                return Response({'details': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            if not request.user.is_staff:
                return Response({'details': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.serializer(element).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(responses={
                            200: openapi.Response(
                                description='Успешно добавили',
                                schema=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                      properties={
                                                          'decay_information': openapi.Schema(
                                                                type=openapi.TYPE_OBJECT,
                                                                properties={
                                                                    'decay_id': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                                    'decay_elements_count': openapi.Schema(type=openapi.TYPE_NUMBER)
                                                                })
                                                      })
                            ),
                            400: openapi.Response(
                                description='Не смогли добавить',
                                schema=error_schema
                            ),
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            )
    })
    @method_permission_classes([IsAuth])
    def post(self, request, element_id):
        decay, is_created = Decay.objects.get_or_create(
            creator = request.user,
            status = 'draft',
        )
        if Element_Decay.objects.filter(element=element_id, decay=decay.decay_id).exists():
            return Response({'details': 'Уже добавлено'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            Element_Decay.objects.create(
                decay = Decay.objects.get(decay_id=decay.decay_id),
                element = Element.objects.get(element_id=element_id)
            )
            decay_id = request.user.user_decays.all().filter(status='draft').first().decay_id
            decay_elements_count = Element_Decay.objects.filter(decay_id=decay.decay_id).count()
            return Response({'decay_information': {'decay_id': decay_id, 'decay_elements_count': decay_elements_count}}, status=status.HTTP_200_OK)
    

    @swagger_auto_schema(request_body=serializer,
                         responses={
                            200: openapi.Response(
                                description='Успешное изменение элемента',
                                schema=ElementSerializer
                            ),
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого элемента',
                                schema=error_schema
                            )
    })
    @method_permission_classes([IsManager])
    def put(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        changed_element = self.serializer(element, request.data, partial=True)
        if changed_element.is_valid():
            changed_element.save()
            return Response(changed_element.data, status=status.HTTP_200_OK)
        return Response(changed_element.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(responses={
                            200: openapi.Response(
                                description='Успешное изменение элемента',
                                schema=ElementSerializer
                            ),
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого элемента',
                                schema=error_schema
                            ),
                            400: openapi.Response(
                                description='Элемент уже удален',
                                schema=error_schema
                            )
    })
    @method_permission_classes([IsManager])
    def delete(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        if element.status != 'deleted':
            element.status = 'deleted'
            if deleteImg(element.img_url) == 'success':
                element.img_url = ''
                element.save()
                return Response(self.serializer(element).data, status=status.HTTP_200_OK)
            element.save()
            return Response({'details': 'Удаление не удалось'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'details': 'Элемент уже удален'}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@swagger_auto_schema(method='post', 
                     consumes=['multipart/form-data'], 
                     request_body=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'img': openapi.Schema(type=openapi.TYPE_FILE)
                        },
                        required=['img']
                     ),
                     responses={
                        403: openapi.Response(
                            description='Нет доступа',
                            schema=error_schema
                        ),
                        202: openapi.Response(
                            description='Картинка успешко загружена',
                            schema=ElementSerializer
                        ),
                        400: openapi.Response(
                            description='Ошибка загрузки',
                            schema=error_schema
                        ),
                        404: openapi.Response(
                            description='Такого элемента нет',
                            schema=error_schema
                        )
})
@api_view(['post'])
@authentication_classes([AuthBySSID])
@permission_classes([IsManager])
def elementAddImg(request, element_id):
    element = get_object_or_404(Element, element_id=element_id)
    img = request.FILES.get('img')
    try:
        past_url = element.img_url
        element.img_url = addImg(img)
        dfg = deleteImg(past_url)
        element.save()
        return Response(ElementSerializer(element).data, status=status.HTTP_202_ACCEPTED)
    except:
        return Response({'details': 'Ошибка загрузки'}, status=status.HTTP_400_BAD_REQUEST)


class elementDecayMethods(APIView):
    serializer = ElementDecaySerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(responses={
                            404: openapi.Response(
                                description='Уже удалено/не существует',
                                schema=error_schema
                            ),
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            200: openapi.Response(
                                description='Успешно удалено',
                                schema=ElementDecaySerializer(many=True)
                            )
    })
    @method_permission_classes([IsAuth])
    def delete(self, request, element_id, decay_id):
        element_decay = get_object_or_404(Element_Decay, element=element_id, decay=decay_id)
        element_decay.delete()
        elements_decay = Element_Decay.objects.filter(decay=decay_id)
        return Response(self.serializer(elements_decay, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'quantity': openapi.Schema(type=openapi.TYPE_STRING)
                            },
                         ),
                         responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого элемента в таком распаде',
                                schema=error_schema
                            ),
                            200: openapi.Response(
                                description='Успешное изменение поля м-м',
                                schema=ElementDecaySerializer(many=True)
                            )
    })
    @permission_classes([IsAuth])
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
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(manual_parameters=[
                            openapi.Parameter(
                                'start_date',
                                openapi.IN_QUERY,
                                description='Начальная дата',
                                type=openapi.TYPE_STRING
                            ),
                            openapi.Parameter(
                                'end_date',
                                openapi.IN_QUERY,
                                description='Конечная дата',
                                type=openapi.TYPE_STRING
                            ),
                            openapi.Parameter(
                                'status',
                                openapi.IN_QUERY,
                                description='Статус (completed/formed/rejected)',
                                type=openapi.TYPE_STRING
                            )
                         ],
                         responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            400: openapi.Response(
                                description='Неправильные фильтры',
                                schema=error_schema
                            ),
                            200: openapi.Response(
                                description='Успешное применение фильтра',
                                schema=DecaySerializer(many=True)
                            ),
    })
    @method_permission_classes([IsAuth])
    def get(self, request):
        acceptable_statuses = [
            'completed',
            'formed',
            'rejected'
        ]

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        if request.user.is_staff:
            decays = Decay.objects.filter(status__in=acceptable_statuses)
        else:
            decays = Decay.objects.filter(status__in=acceptable_statuses, creator=request.user)

        filter = {}
        if start_date:
            start_date = parse_datetime(start_date)
            if start_date is None:
                return Response({'details': 'start_date'}, status=status.HTTP_400_BAD_REQUEST)
            filter['date_of_creation__gte'] = start_date
        if end_date:
            end_date = parse_datetime(end_date)
            if end_date is None:
                return Response({'details': 'end_date'}, status=status.HTTP_400_BAD_REQUEST)
            filter['date_of_creation__lte'] = end_date
        if status_filter:
            if not status_filter in acceptable_statuses:
                return Response({'details': 'status'}, status=status.HTTP_400_BAD_REQUEST)
            filter['status'] = status_filter
        
        return Response(self.serializer(decays.filter(**filter), many = True).data, status=status.HTTP_200_OK)
    
class decayMethods(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Такого распада не существует',
                                schema=error_schema
                            ),
                            200: openapi.Response(
                                description='Успешное получение распада',
                                schema=DecaySerializer
                            ),
    })
    @method_permission_classes([IsAuth])
    def get(self, request, decay_id):
        decay = get_object_or_404(Decay, decay_id=decay_id)
        if decay.creator != request.user and not request.user.is_staff:
            return Response({'details:', 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.serializer(decay).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(request_body=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'pass_time': openapi.Schema(type=openapi.TYPE_STRING)
                            } 
                         ),
                         responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого распада',
                                schema=error_schema
                            ),
                            200: openapi.Response(
                                description='Успешное изменение',
                                schema=ok_schema
                            )
    })
    @method_permission_classes([IsAuth])
    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, creator = request.user, decay_id=decay_id)
        decay.pass_time = request.data['pass_time']
        decay.save()
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class formingDecay(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            400: openapi.Response(
                                description='Пустое(-ые) поля',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого распада',
                                schema=error_schema
                            ),
                            202: openapi.Response(
                                description='Успешное формирование заявки',
                                schema=DecaySerializer
                            ),
    })
    @method_permission_classes([IsAuth])
    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, creator = request.user, decay_id=decay_id)
        elements = decay.decay_elements.all()
        if not decay.pass_time is None and decay.pass_time != '':
            for element in elements:
                if element.quantity is None or element.quantity == '':
                    return Response({'details': 'quantity'}, status=status.HTTP_400_BAD_REQUEST)
            decay.status = 'formed'
            decay.date_of_formation = timezone.now()
            decay.save()
            return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'details': 'pass_time'}, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого распада',
                                schema=error_schema
                            ),
                            202: openapi.Response(
                                description='Успешное удаление распада',
                                schema=DecaySerializer
                            ),
    })
    @method_permission_classes([IsAuth])
    def delete(self, request, decay_id):
        decay = get_object_or_404(Decay, creator = request.user, decay_id=decay_id)
        decay.status = 'deleted'
        decay.date_of_formation = timezone.now()
        decay.save()
        return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)

class moderateDecay(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(request_body=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'accept': openapi.Schema(type=openapi.TYPE_STRING)
                            },
                            required=['accept']
                         ),
                         responses={
                            403: openapi.Response(
                                description='Нет доступа',
                                schema=error_schema
                            ),
                            404: openapi.Response(
                                description='Нет такого распада',
                                schema=error_schema
                            ),
                            400: openapi.Response(
                                description='Заявка не сформирована/неверное действие(accept)',
                                schema=error_schema
                            ),
                            202: openapi.Response(
                                description='Успешное отклонение',
                                schema=DecaySerializer
                            ),
    })
    @method_permission_classes([IsManager])
    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        accept = request.data.get('accept')
        if decay.status == 'formed':
            if accept == 'false':
                decay.status = 'rejected'
                decay.moderator = request.user
                decay.date_of_finish = timezone.now()
                decay.save()
                return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
            elif accept == 'true':
                elements = decay.decay_elements.all()
                for element in elements:
                    try:
                        element.remaining_quantity = HalfLifeCalculation.half_life_calculation(decay.pass_time, 
                                                                                                element.quantity, 
                                                                                                element.element.period_time)
                    except NameError:
                        element.remaining_quantity = 'Неверный формат входных данных'
                    except ValueError:
                        element.remaining_quantity = 'Неверный формат единиц измерения'
                    element.save()
                decay.moderator = request.user
                decay.status = 'completed'
                decay.date_of_finish = timezone.now()
                decay.qr = generate_decay_qr(decay)
                decay.save()
                return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({'details': 'Неверное действие'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'details': 'Заявка не сформирована'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@swagger_auto_schema(method='post',
                     request_body=SwaggerCustomUserSerializer,
                     responses={
                        400: openapi.Response(
                            description='Ошибка регистрации',
                            schema=error_schema
                        ),
                        200: openapi.Response(
                            description='Успешная регистрация',
                            schema=CustomUserSerializer
                        ),
})
@api_view(['post'])
@authentication_classes([])
@permission_classes([AllowAny])
def registration_view(request):
    if CustomUser.objects.filter(email=request.data['email']).exists():
        return Response({'details': 'email exist'}, status=status.HTTP_400_BAD_REQUEST)
    serializer = CustomUserSerializer(data=request.data)
    if serializer.is_valid():
        CustomUser.objects.create_user(email=serializer.data['email'],
                                       password=serializer.data['password'])
        user = authenticate(request, email=request.data['email'], password=request.data['password'])
        return Response(CustomUserSerializer(user).data, status=status.HTTP_200_OK)
    return Response({'details': 'registration failed'}, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='put', 
                     request_body=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'password': openapi.Schema(type=openapi.TYPE_STRING)
                        }
                     ),
                     responses={
                        403: openapi.Response(
                            description='Нет доступа',
                            schema=error_schema
                        ),
                        200: openapi.Response(
                            description='Нет доступа',
                            schema=CustomUserSerializer
                        ),
                     }
)
@api_view(['put'])
@authentication_classes([AuthBySSID])
@permission_classes([IsAuth])
def account_view(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if email:
        ssid = request.COOKIES.get('session_id')
        try:
            session_storage.set(ssid, email)
        except Exception:
            return Response({'details': 'Session not found'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.email = email
        request.user.save()
    if password:
        request.user.set_password(password)
        request.user.save()
        authenticate(request, email=request.user.email, password=password)
    return Response(CustomUserSerializer(request.user).data, status=status.HTTP_200_OK)

class attributeListMethods(APIView):
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={
                                                         'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                         'value': openapi.Schema(type=openapi.TYPE_STRING)
                                                     },
                                                     required=['name']),
                        responses={
                            200: openapi.Response(
                                description='Успешное создании атрибута',
                                schema=AttributeElementSerializer
                            )
                        })
    @method_permission_classes([IsManager])
    def post(self, request, element_id):
        attribute_name = request.data.get('name', '')
        attribute_value = request.data.get('value', '')
        element = get_object_or_404(Element, pk=element_id)
        if Attribute.objects.filter(name=attribute_name).exists():
            attribute = Attribute.objects.get(name=attribute_name)
        else:
            attribute = Attribute.objects.create(name=attribute_name)
        element_attribute, created = Attribute_Element.objects.get_or_create(element=element, attribute=attribute)
        element_attribute.value = attribute_value
        element_attribute.save()
        return Response(AttributeElementSerializer(element_attribute).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(responses={
                            200: openapi.Response(
                                description='Успешное получение атрибутов',
                                schema=ElementForAttributesSerializer
                            )
                        })
    @method_permission_classes([AllowAny])
    def get(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        return Response(ElementForAttributesSerializer(element).data, status=status.HTTP_200_OK)
        
class attributeDetailMethods(APIView):
    authentication_classes = [AuthBySSID]

    @swagger_auto_schema(responses={
                            200: openapi.Response(
                                description='Успешное удаление атрибута',
                                schema=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                      properties={
                                                          'id': openapi.Schema(type=openapi.TYPE_NUMBER)
                                                      })
                            ),
                        })
    @method_permission_classes([IsManager])
    def delete(self, request, element_id, attribute_id):
        element = get_object_or_404(Element, pk=element_id)
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        get_object_or_404(Attribute_Element, attribute=attribute, element=element).delete()
        return Response({'id': attribute.attribute_id}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={
                                                         'value': openapi.Schema(type=openapi.TYPE_STRING)
                                                     }),
                        responses={
                            200: openapi.Response(
                                description='Успешное создании атрибута',
                                schema=ok_schema
                            )
                        })
    @method_permission_classes([IsManager])
    def put(self, request, element_id, attribute_id):
        element = get_object_or_404(Element, pk=element_id)
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        value = request.data.get('value', '')
        element_attribute = get_object_or_404(Attribute_Element, attribute=attribute, element=element)
        element_attribute.value = value
        element_attribute.save()
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        