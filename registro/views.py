import cv2

import os

from django.shortcuts import render, redirect

from .forms import FuncionarioForm, ColetaFacesForm

from .models import Funcionario, ColetaFaces

from django.http import StreamingHttpResponse

from registro.camera import VideoCamera

from django.core.files import File 

camera_detection = VideoCamera()  # Instância da classe VideoCamera

# Captura o frame com face detectada
def gen_detect_face(camera_detection):
    while True:
        frame = camera_detection.detect_face()  
        if frame is None:
          continue
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

# Cria streaming para detecção facial
def face_detection(request):
      return StreamingHttpResponse(gen_detect_face(camera_detection),content_type='multipart/x-mixed-replace; boundary=frame')
    
def criar_funcionario(request):
    
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, request.FILES)

        if form.is_valid():
            funcionario = form.save()
            # 1. POST VÁLIDO: Sai da função com um REDIRECIONAMENTO
            return redirect('criar_coleta_faces', funcionario_id=funcionario.id)
        
        # 2. POST INVÁLIDO: O 'form' existe com os erros, e o código segue para o render final.
        # Não precisa de 'else' aqui, e remova a linha 'form = FuncionarioForm()' se ela estiver no seu código.
    
    else: # 3. MÉTODO GET: Inicializa o formulário vazio
        form = FuncionarioForm()

    # 4. Retorno ÚNICO: Serve para GET e para POST inválido.
    return render(request, 'criar_funcionario.html', {'form': form}) 

# Cria uma função para extrair e retornar o file_path
def extract(camera_detection, funcionario_slug):
    amostra = 0 # Amostras inicial
    numeroAmostras = 10 # Numero de Amostra para extrair
    largura, altura = 220, 220  # largura, altura forma quadradinho
    file_paths = [] # lista de path das amostras

    while amostra < numeroAmostras: # faz um loop até 10 amostra
        ret, frame = camera_detection.get_camera() # pega frame da camera (objeto 
        crop = camera_detection.sample_faces(frame)  # Captura as faces

        if crop is not None: # se não for None, 
           amostra += 1 # conta 1

           face = cv2.resize(crop, (largura, altura)) # resize 
           imagemCinza = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY) # Passa para cinza

           # Define o caminho da imagem
           file_name_path = f'./tmp/{funcionario_slug}_{amostra}.jpg' # exemplo> 
           cv2.imwrite(file_name_path, imagemCinza)
           file_paths.append(file_name_path) # Adiciona na lista
        else:
            print("Face não encontrada")

        if amostra >= numeroAmostras: 
            break # deu 10 amostra para

    return file_paths

def face_extract(context, funcionario): 
 num_coletas = ColetaFaces.objects.filter(
    funcionario__slug=funcionario.slug).count()
 print(num_coletas) # Quantidade de imagens que funcionario tem cadrastrado

 if num_coletas >= 10: # Verifica se limte de coletas foi atingido
        context['erro'] = 'Limite máximo de coletas atingido.'

 else:
      files_paths = extract(camera_detection, funcionario.slug) # passa camera e
      print(files_paths) # paths Rostros

      for path in files_paths:
          # Cria uma instância de coletaFaces e salva a imagem
          coleta_face = ColetaFaces.objects.create(funcionario=funcionario)
          coleta_face.image.save(os.path.basename(path), open(path, 'rb'))
          os.remove(path) # Remove o arquivo temporário após o salvamento

       # Atualiza o contexto com as coletas salvas
      context['file_paths'] = ColetaFaces.objects.filter(
                funcionario__slug=funcionario.slug)
      context['extracao_ok'] = True
 
 return context

#Criar coleta de faces (Registro)
def criar_coleta_faces(request, funcionario_id):
    # Use get_object_or_404 para evitar o erro DoesNotExist
    funcionario = Funcionario.objects.get(id=funcionario_id)
    botao_clicado = request.GET.get('clicked', 'False') == 'True'

    # 1. BUSCA DE COLETAS ATUAIS
    coletas_atuais = ColetaFaces.objects.filter(funcionario=funcionario)

    # 2. VARIÁVEL DE CONTROLE CRÍTICA: Define se já temos imagens salvas
    inicial_extracao_ok = coletas_atuais.exists() 
    # O valor será True se houver coletas, ou False se não houver.

    context = {
        'funcionario': funcionario,
        'file_paths': coletas_atuais,
        'face_detection': face_detection, 
        'valor_botao': botao_clicado,
        'erro': None,
        'sucesso': None,
        # 3. NOVO: Define a chave de controle para o template
        'extracao_ok': inicial_extracao_ok, 
        'coletas_existentes': coletas_atuais 
    }
    # SOMENTE CHAME A EXTRAÇÃO SE O BOTÃO FOI CLICADO
    if botao_clicado:
        print("Extração de Imagens solicitada...")

        # AQUI OCORRE A EXTRAÇÃO E SALVAMENTO DEMORADO
        context = face_extract(context, funcionario) 

        # Importante: Redirecione após POST/GET de ação para evitar reenvio
        if context.get('extracao_ok') or context.get('erro'):

        # Redireciona para o mesmo URL, mas sem o parâmetro 'clicked=True'
            return redirect('criar_coleta_faces', funcionario_id=funcionario.id) 

    # Renderiza o template com o streaming (sem extração)
    return render(request, 'criar_coleta_faces.html', context)











