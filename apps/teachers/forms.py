from django import forms
from .models import TeacherSubject



class TeacherAllocationForm(forms.ModelForm):
    class Meta:
        model = TeacherSubject
        fields = ['teacher', 'class_room', 'subject']
        
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Estilização consistente SOTARQ
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition'
            })

        if school:
            # RIGOR SOTARQ: O campo no seu User é 'tenant', não 'school'
            # 'teacher__user' acessa o usuário, 'tenant' acessa a escola
            self.fields['teacher'].queryset = self.fields['teacher'].queryset.filter(
                user__tenant=school
            )
            
            # Filtro de Turmas ativas para o tenant (se o modelo Class tiver tenant)
            # Caso contrário, filtramos apenas pelo ano ativo como já estava
            self.fields['class_room'].queryset = self.fields['class_room'].queryset.filter(
                academic_year__is_active=True
            )






