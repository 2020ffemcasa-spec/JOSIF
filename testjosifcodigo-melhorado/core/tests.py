import json
from datetime import time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Atividade, Feedback, Materia, Meta

SENHA = 'senha-forte-123'


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana@ex.com', 'ana@ex.com', SENHA, first_name='Ana')
        self.outro = User.objects.create_user('bia@ex.com', 'bia@ex.com', SENHA, first_name='Bia')
        self.client.login(username='ana@ex.com', password=SENHA)


class ModelTests(TestCase):
    def test_duracao_considera_minutos(self):
        a = Atividade(hora_inicio=time(9, 0), hora_fim=time(9, 45))
        self.assertEqual(a.get_duracao(), 0.75)

    def test_duracao_atravessando_meia_noite(self):
        a = Atividade(hora_inicio=time(23, 0), hora_fim=time(1, 0))
        self.assertEqual(a.get_duracao(), 2.0)

    def test_meta_com_prazo_vencido_fica_atrasada(self):
        ontem = timezone.localdate() - timedelta(days=1)
        meta = Meta(meta_progresso=80, progresso_atual=70, prazo=ontem)
        self.assertEqual(meta.calcular_status(), 'behind')

    def test_meta_sem_prazo_usa_so_o_progresso(self):
        meta = Meta(meta_progresso=80, progresso_atual=70)
        self.assertEqual(meta.calcular_status(), 'on-track')


class PaginasTests(BaseTestCase):
    def test_todas_as_paginas_renderizam(self):
        materia = Materia.objects.create(usuario=self.user, nome='Matemática')
        Atividade.objects.create(
            usuario=self.user, materia=materia, titulo='Álgebra',
            dia_semana=0, hora_inicio=time(8, 0), hora_fim=time(9, 30),
        )
        Meta.objects.create(usuario=self.user, titulo='Meta 1')
        for nome in ('dashboard', 'materias', 'cronogramas', 'metas', 'relatorios', 'configuracoes'):
            with self.subTest(pagina=nome):
                resposta = self.client.get(reverse(f'core:{nome}'))
                self.assertEqual(resposta.status_code, 200)

    def test_cronograma_mostra_a_atividade_na_grade(self):
        Atividade.objects.create(
            usuario=self.user, titulo='Revisão de Álgebra',
            dia_semana=2, hora_inicio=time(8, 0), hora_fim=time(9, 0),
        )
        resposta = self.client.get(reverse('core:cronogramas'))
        self.assertContains(resposta, 'Revisão de Álgebra')

    def test_materias_ordenadas_por_prioridade(self):
        Materia.objects.create(usuario=self.user, nome='B-baixa', prioridade='low')
        Materia.objects.create(usuario=self.user, nome='C-alta', prioridade='high')
        Materia.objects.create(usuario=self.user, nome='A-media', prioridade='medium')
        resposta = self.client.get(reverse('core:materias'))
        nomes = [m.nome for m in resposta.context['materias']]
        self.assertEqual(nomes, ['C-alta', 'A-media', 'B-baixa'])


class SegurancaTests(BaseTestCase):
    def test_excluir_exige_post(self):
        materia = Materia.objects.create(usuario=self.user, nome='Física')
        url = reverse('core:materia_delete', args=[materia.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(Materia.objects.filter(pk=materia.pk).exists())
        self.client.post(url)
        self.assertFalse(Materia.objects.filter(pk=materia.pk).exists())

    def test_nao_exclui_materia_de_outro_usuario(self):
        materia = Materia.objects.create(usuario=self.outro, nome='Química')
        resposta = self.client.post(reverse('core:materia_delete', args=[materia.pk]))
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(Materia.objects.filter(pk=materia.pk).exists())

    def test_logout_exige_post(self):
        self.assertEqual(self.client.get(reverse('core:logout')).status_code, 405)
        resposta = self.client.post(reverse('core:logout'))
        self.assertEqual(resposta.status_code, 302)

    def test_meta_nao_aceita_materia_de_outro_usuario(self):
        meta = Meta.objects.create(usuario=self.user, titulo='Minha meta')
        materia_alheia = Materia.objects.create(usuario=self.outro, nome='Alheia')
        self.client.post(reverse('core:meta_edit', args=[meta.pk]), {
            'titulo': 'Minha meta', 'materia': materia_alheia.pk,
            'meta_progresso': 80, 'progresso_atual': 10,
        })
        meta.refresh_from_db()
        self.assertIsNone(meta.materia_id)


class RelatoriosTests(BaseTestCase):
    def _atividade(self, materia=None, concluida=False, titulo='Estudo',
                   inicio=time(8, 0), fim=time(9, 30)):
        return Atividade.objects.create(
            usuario=self.user, materia=materia, titulo=titulo, dia_semana=0,
            hora_inicio=inicio, hora_fim=fim, concluida=concluida,
        )

    def test_concluir_define_data_e_reabrir_limpa(self):
        a = self._atividade()
        url = reverse('core:atividade_toggle', args=[a.pk])
        self.client.post(url)
        a.refresh_from_db()
        self.assertTrue(a.concluida)
        self.assertEqual(a.data_conclusao, timezone.localdate())
        self.client.post(url)
        a.refresh_from_db()
        self.assertFalse(a.concluida)
        self.assertIsNone(a.data_conclusao)

    def test_horas_dos_relatorios_vem_das_atividades_concluidas(self):
        self._atividade(concluida=True)    # 1,5 h
        self._atividade(concluida=False)   # não conta
        resposta = self.client.get(reverse('core:relatorios') + '?periodo=tudo')
        self.assertEqual(resposta.context['horas_estudadas'], 1.5)

    def test_distribuicao_usa_titulo_quando_nao_ha_materia(self):
        self._atividade(concluida=True, titulo='Português')
        resposta = self.client.get(reverse('core:relatorios') + '?periodo=tudo')
        self.assertEqual(resposta.context['distribuicao'][0]['nome'], 'Português')

    def test_distribuicao_usa_nome_da_materia_quando_informada(self):
        materia = Materia.objects.create(usuario=self.user, nome='Matemática')
        self._atividade(materia=materia, concluida=True, titulo='Lista 3')
        resposta = self.client.get(reverse('core:relatorios') + '?periodo=tudo')
        self.assertEqual(resposta.context['distribuicao'][0]['nome'], 'Matemática')

    def test_horas_do_cronograma_so_das_concluidas(self):
        self._atividade(concluida=True)
        self._atividade(concluida=False)
        resposta = self.client.get(reverse('core:cronogramas'))
        self.assertEqual(resposta.context['horas_semana'], 1.5)

    def test_metas_concluidas_contam_como_atividades_concluidas(self):
        self._atividade(concluida=True)
        Meta.objects.create(usuario=self.user, titulo='Meta', meta_progresso=80, progresso_atual=90)
        resposta = self.client.get(reverse('core:relatorios'))
        self.assertEqual(resposta.context['atividades_concluidas'], 2)

    def test_materia_cadastrada_aparece_nos_relatorios(self):
        url = reverse('core:relatorios')
        self.assertEqual(self.client.get(url).context['total_materias'], 0)
        Materia.objects.create(usuario=self.user, nome='Física')
        self.assertEqual(self.client.get(url).context['total_materias'], 1)

    def test_materia_excluida_some_dos_relatorios(self):
        materia = Materia.objects.create(usuario=self.user, nome='Química')
        self._atividade(materia=materia)
        self.client.post(reverse('core:materia_delete', args=[materia.pk]))
        self.assertEqual(self.client.get(reverse('core:relatorios')).context['total_materias'], 0)


class ConfiguracoesTests(BaseTestCase):
    def _salvar(self, payload):
        return self.client.post(
            reverse('core:configuracoes'), data=json.dumps(payload), content_type='application/json'
        )

    def test_trocar_email_mantem_o_login_funcionando(self):
        resposta = self._salvar({'email': 'novo@ex.com'})
        self.assertEqual(resposta.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'novo@ex.com')
        self.assertEqual(self.user.username, 'novo@ex.com')

    def test_nao_permite_email_de_outra_conta(self):
        resposta = self._salvar({'email': 'bia@ex.com'})
        self.assertEqual(resposta.status_code, 400)

    def test_cor_em_rgb_vira_hex_da_paleta(self):
        self._salvar({'cor_primaria': 'rgb(40, 120, 255)'})
        self.user.configuracao.refresh_from_db()
        self.assertEqual(self.user.configuracao.cor_primaria, '#2878FF')

    def test_cor_escolhida_vai_para_todas_as_paginas(self):
        self._salvar({'cor_primaria': '#7c3aed'})
        for nome in ('dashboard', 'materias', 'cronogramas'):
            with self.subTest(pagina=nome):
                resposta = self.client.get(reverse(f'core:{nome}'))
                self.assertContains(resposta, '--accent: #7c3aed')
                self.assertContains(resposta, '.ico-svg { color: var(--accent); }')

    def test_aba_privacidade_renderiza(self):
        resposta = self.client.get(reverse('core:configuracoes'))
        self.assertContains(resposta, 'id="sec-privacidade"')

    def test_troca_de_senha_funciona(self):
        resposta = self.client.post(reverse('core:alterar_senha'), {
            'old_password': SENHA,
            'new_password1': 'nova-senha-456',
            'new_password2': 'nova-senha-456',
        })
        self.assertEqual(resposta.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nova-senha-456'))

    def test_troca_de_senha_recusa_senha_atual_errada(self):
        resposta = self.client.post(reverse('core:alterar_senha'), {
            'old_password': 'senha-errada',
            'new_password1': 'nova-senha-456',
            'new_password2': 'nova-senha-456',
        })
        self.assertEqual(resposta.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(SENHA))

    def test_privacidade_mostra_email_do_usuario(self):
        resposta = self.client.get(reverse('core:configuracoes'))
        self.assertContains(resposta, self.user.email)

    def test_feedback_salva(self):
        resposta = self.client.post(reverse('core:enviar_feedback'), {
            'tipo': 'bug', 'email': 'contato@ex.com', 'mensagem': 'A tela X travou.',
        })
        self.assertEqual(resposta.status_code, 302)
        fb = Feedback.objects.get()
        self.assertEqual(fb.usuario, self.user)
        self.assertEqual(fb.tipo, 'bug')
        self.assertEqual(fb.email, 'contato@ex.com')

    def test_feedback_mensagem_curta_recusada(self):
        # Mensagem com menos de 5 caracteres é recusada (form HTML => redirect + erro)
        self.client.post(reverse('core:enviar_feedback'), {'mensagem': 'oi'})
        self.assertFalse(Feedback.objects.exists())

    def test_exportar_dados_retorna_anexo(self):
        Materia.objects.create(usuario=self.user, nome='Matemática')
        resposta = self.client.get(reverse('core:exportar_dados'))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('attachment', resposta['Content-Disposition'])
        self.assertEqual(resposta.json()['materias'][0]['nome'], 'Matemática')

    def test_excluir_conta_exige_confirmacao(self):
        self.client.post(reverse('core:excluir_conta'), {'confirmacao': 'errado'})
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.client.post(reverse('core:excluir_conta'), {'confirmacao': 'EXCLUIR'})
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())


class SemanasDoCronogramaTests(BaseTestCase):
    def _data_da_semana(self, offset, dia=0):
        hoje = timezone.localdate()
        return hoje - timedelta(days=hoje.weekday()) + timedelta(weeks=offset, days=dia)

    def _criar(self, titulo, data):
        return Atividade.objects.create(
            usuario=self.user, titulo=titulo, dia_semana=data.weekday(), data=data,
            hora_inicio=time(8, 0), hora_fim=time(9, 0),
        )

    def test_atividade_so_aparece_na_propria_semana(self):
        self._criar('Desta semana', self._data_da_semana(0))
        url = reverse('core:cronogramas')
        self.assertContains(self.client.get(url), 'Desta semana')
        self.assertNotContains(self.client.get(url + '?semana=-1'), 'Desta semana')
        self.assertNotContains(self.client.get(url + '?semana=1'), 'Desta semana')

    def test_semana_passada_mostra_o_que_existia_nela(self):
        self._criar('Semana passada', self._data_da_semana(-1, 2))
        url = reverse('core:cronogramas')
        resposta = self.client.get(url + '?semana=-1')
        self.assertContains(resposta, 'Semana passada')
        self.assertEqual(resposta.context['total_atividades'], 1)
        self.assertEqual(self.client.get(url).context['total_atividades'], 0)

    def test_criar_olhando_a_semana_passada_grava_nela(self):
        url = reverse('core:cronogramas') + '?semana=-1'
        self.client.post(url, {
            'titulo': 'Antiga', 'dia_semana': 1, 'hora_inicio': '08:00', 'hora_fim': '09:00',
        })
        atividade = Atividade.objects.get(titulo='Antiga')
        self.assertEqual(atividade.data, self._data_da_semana(-1, 1))
