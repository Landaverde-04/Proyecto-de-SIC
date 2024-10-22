from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def hola(request):
    return HttpResponse("<h1>Prueba</h1>")
def inicio(request):
    return render(request, 'paginas/inicio.html')