from django.shortcuts import render, redirect
from django.db import IntegrityError, connection
from django.http import HttpResponseBadRequest
from .models import Element, Decay, Element_Decay
from django.contrib.auth import get_user_model

curr_user_id = 1

def addElementToDecay(request):
    if request.method == 'POST':
        User = get_user_model()
        element_id = request.POST.get('element_id')
        decay = Decay.objects.filter(creator=curr_user_id, status='draft').first()
        if decay is None:
            new_decay = Decay(
                status = 'draft',
                creator = User.objects.get(id=curr_user_id)
            )
            new_decay.save()
            decay_id = new_decay.decay_id
        else:
            decay_id = decay.decay_id
        try:
            new_element_decay = Element_Decay(
                decay = Decay.objects.get(decay_id=decay_id),
                element = Element.objects.get(element_id=element_id),
            )
            new_element_decay.save()
        except IntegrityError:
            pass

    return redirect('home')

def deleteDecay(request):
    decay_id = request.POST.get('decay_id')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE radioactive_elements_app_decay SET status = 'deleted' WHERE decay_id = %s", decay_id)
    return redirect('home')

def getDecayInformation(user_id):
    decay = Decay.objects.filter(creator=user_id, status='draft').first()
    if decay is None:
        decay_elements_count = 0 
        decay_id = 0
    else:
        decay_elements_count = Element_Decay.objects.filter(decay_id=decay.decay_id).count()
        decay_id = decay.decay_id

    return {'decay_elements_count': decay_elements_count, 
            'decay_id': decay_id}

def getService(request, element_id):
    element = Element.objects.get(element_id=element_id)

    return render(request, 'service.html', {'element': element})

def getServices(request):
    search_number = request.GET.get('atomic_mass', '')
    elements = Element.objects.filter(atomic_mass__contains=search_number)
    decay_information = getDecayInformation(curr_user_id)

    return render(request, 'services.html', {'search_number': search_number, 
                                             'elements': elements, 
                                             'decay_information': decay_information})

def getDecay(request, decay_id):
    decay = Decay.objects.filter(decay_id=decay_id).first()
    if decay is None:
        decay_elements = {}
        pass_time = ''
        permission = 0
    elif decay.status == 'draft': 
        decay_elements = Element_Decay.objects.filter(decay_id=decay_id).select_related('element')
        pass_time = decay.pass_time
        permission = 1
    else:
        decay_elements = {}
        pass_time = ''
        permission = 0

    return render(request, 'decay.html', {'decay_id': decay_id,
                                          'decay_elements': decay_elements, 
                                          'pass_time': pass_time,
                                          'permission': permission})