from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views


class CustomLoginView(auth_views.LoginView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('contratos')  # Redireciona para a URL de contratos
        return super().dispatch(request, *args, **kwargs)
    

def custom_404(request, exception):
    return render(request, '404.html', status=404)


