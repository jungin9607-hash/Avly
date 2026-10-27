"""로컬 실행 환경 설정(경로 탐색, 키 읽기)."""
import os
import re
import sys
from pathlib import Path


def find_backend_root(start=None, explicit=None):
    def local_path(value):
        value=str(value).strip()
        if sys.platform.startswith('linux') and re.match(r'^[A-Za-z]:[\\/]',value):
            value='/mnt/'+value[0].lower()+'/'+value[3:].replace('\\','/')
        return Path(value).expanduser()
    if explicit:
        candidate=local_path(explicit).resolve()
        if not candidate.is_dir() or not (candidate/'model').is_dir():
            raise FileNotFoundError('BACKEND_DIR은 model 폴더가 있는 backend 디렉터리로 지정하세요.')
        return candidate
    here=local_path(start or Path.cwd()).resolve()
    for parent in [here,*here.parents]:
        if parent.name=='backend' and (parent/'model').is_dir():return parent
        candidate=parent/'backend'
        if (candidate/'model').is_dir():return candidate.resolve()
    raise FileNotFoundError('backend/model 폴더를 찾지 못했습니다. WSL의 Avly 폴더를 열거나 BACKEND_DIR에 /home/사용자/Avly/backend를 지정하세요.')

def backend_path(value, backend):
    value=str(value).strip()
    if sys.platform.startswith('linux') and re.match(r'^[A-Za-z]:[\\/]',value):
        value='/mnt/'+value[0].lower()+'/'+value[3:].replace('\\','/')
    path=Path(value).expanduser()
    return (path if path.is_absolute() else backend/path).resolve()

def choose_local_video(backend, graphical=False):
    extensions={'.mp4','.webm','.avi','.mov','.mkv','.m4v'}
    upload_dir=backend/'uploads'
    if graphical:
        window=None
        try:
            import tkinter as tk
            from tkinter import filedialog
            window=tk.Tk();window.withdraw()
            chosen=filedialog.askopenfilename(title='분석할 영상 선택',
                initialdir=str(upload_dir if upload_dir.is_dir() else backend),
                filetypes=[('동영상','*.mp4 *.webm *.avi *.mov *.mkv *.m4v'),('모든 파일','*.*')])
            if not chosen:raise SystemExit('영상 선택을 취소했습니다.')
            path=backend_path(chosen,backend)
            if path.is_file() and path.suffix.lower() in extensions:return path
            print('지원되는 영상 파일을 선택하세요. 터미널 선택으로 전환합니다.')
        except (ImportError,RuntimeError) as exc:
            print('파일 선택 창을 사용할 수 없어 터미널에서 선택합니다.')
        except Exception as exc:
            if type(exc).__name__!='TclError':raise
            print('WSL의 GUI 표시를 사용할 수 없어 터미널에서 선택합니다.')
        finally:
            if window is not None:window.destroy()
    videos=sorted((p for p in upload_dir.rglob('*') if p.is_file() and p.suffix.lower() in extensions),key=lambda p:str(p).casefold()) if upload_dir.is_dir() else []
    print('\n분석할 영상 선택 · uploads 폴더')
    for i,path in enumerate(videos,1):print(str(i)+'. '+str(path.relative_to(upload_dir)))
    print('번호 또는 영상 경로를 입력하세요. uploads 밖의 파일도 경로로 선택할 수 있습니다. q: 취소')
    while True:
        try:answer=input('영상 선택: ').strip()
        except (EOFError,KeyboardInterrupt):raise SystemExit('영상 선택을 취소했습니다.') from None
        if answer.lower()=='q':raise SystemExit('영상 선택을 취소했습니다.')
        if answer.isdigit() and 1<=int(answer)<=len(videos):return videos[int(answer)-1].resolve()
        if answer.isdigit() or not answer:
            print('목록의 번호나 실제 영상 경로를 입력하세요.');continue
        if len(answer)>=2 and answer[0]==answer[-1] and answer[0] in ('"',"'"):answer=answer[1:-1]
        path=backend_path(answer,backend)
        if path.is_file() and path.suffix.lower() in extensions:return path
        print('영상 파일을 찾지 못했습니다. 상대 경로는 backend 기준입니다.')

def get_secret(name, required=False):
    aliases={'OPENAI_API_KEY':('OPENAI_API_KEY',),
             'law_api':('law_api','LAW_API_OC','LAW_API_KEY')}
    value=next((os.environ[key].strip() for key in aliases.get(name,(name,))
                if os.environ.get(key,'').strip()),None)
    if value and ('발급받은' in value or value.lower() in ('your-api-key','your_openai_api_key','your_law_api_key')):
        raise RuntimeError(name+'에 예시 문구가 들어 있습니다. backend/.env에서 실제 발급값으로 바꿔주세요.')
    if required and not value:
        raise RuntimeError(name+'가 없습니다. backend/.env에 설정하고 프로그램을 다시 실행하세요.')
    return value

def configure_local_runtime(settings):
    backend=find_backend_root(explicit=settings.get('BACKEND_DIR'))
    model=backend/'model'
    try:
        from dotenv import load_dotenv
    except ImportError:
        raise RuntimeError('WSL 가상환경에 model/requirements-model.txt를 설치하고 해당 Python으로 실행하세요.') from None
    env_file=backend/'.env'
    load_dotenv(env_file,override=False,encoding='utf-8-sig')
    video_value=settings.get('VIDEO_FILE')
    if not video_value:video_value=choose_local_video(backend,graphical=settings.get('PICK_VIDEO',False))
    video=backend_path(video_value,backend)
    if not video.is_file():
        raise FileNotFoundError('영상이 없습니다: '+str(video)+'\nVIDEO_FILE을 수정하세요. 상대 경로는 backend 기준입니다.')
    if video.suffix.lower() not in ('.mp4','.webm','.avi','.mov','.mkv','.m4v'):
        raise ValueError('VIDEO_FILE에는 지원되는 영상 파일 한 개를 지정하세요.')
    csv_value=settings.get('CSV_FILE')
    if csv_value:
        csv_path=backend_path(csv_value,backend)
    else:
        csv_path=(Path(__file__).parent/'data'/'fault_table_car_to_car.csv').resolve()
    if not csv_path.is_file():
        raise FileNotFoundError('과실표 CSV를 찾지 못했습니다: '+str(csv_path)+'\nCSV_FILE(또는 FAULT_TABLE_PATH)에 정확한 경로를 지정하세요.')
    results=backend_path(settings['RESULTS_DIR'],backend) if settings.get('RESULTS_DIR') else model/'results'
    results.mkdir(parents=True,exist_ok=True)
    print('Python:',sys.executable)
    print('backend:',backend)
    print('영상:',video)
    print('CSV:',csv_path)
    print('결과 폴더:',results)
    print('환경 파일:',str(env_file) if env_file.is_file() else '없음 · 현재 환경변수 사용')
    print('OpenAI 키:', '설정됨' if get_secret('OPENAI_API_KEY') else '없음 · 새 AI 요청 시 필요')
    print('법령 API 인증값:', '설정됨' if get_secret('law_api') else '없음 · 법령/판례 조회 제한 가능')
    print('분석 중입니다. 완료 후 터미널 기본 설문이 시작됩니다.')
    return {'BACKEND_ROOT':backend,'MODEL_ROOT':model,'PROJECT':model,
            'VIDEO_PATH':video,'CSV_PATH':csv_path,'RESULTS_DIR':results}
