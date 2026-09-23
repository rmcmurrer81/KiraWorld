"""Bound existing local Qwen runtime; never unload another task's model."""
from .world_layout_job import MODEL,MODEL_DIGEST,local_json
import ctypes,subprocess,time

GPU_RESAMPLES=3
GPU_RESAMPLE_SECONDS=2


def resource_admission():
    """Read-only native RAM/VRAM admission; no process stops or model unload."""
    try:
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total_phys',ctypes.c_ulonglong),
                      ('avail_phys',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),
                      ('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),('avail_extended',ctypes.c_ulonglong)]
        status=Memory();status.length=ctypes.sizeof(Memory)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):raise ValueError('RAM status unavailable')
        response=subprocess.run(['C:/Windows/System32/nvidia-smi.exe','--id=0','--query-gpu=memory.free,utilization.gpu',
                                 '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if response.returncode or len(response.stdout)>2048:raise ValueError('GPU status unavailable')
        free,utilization=map(int,response.stdout.strip().split(','))
        return {'available':status.avail_phys>=15*1024**3 and free>=12*1024 and utilization<25,
                'ram_available_bytes':status.avail_phys,'vram_available_mib':free,'gpu_utilization_percent':utilization,
                'required_ram_bytes':15*1024**3,'required_vram_mib':12*1024,'required_gpu_utilization_below':25}
    except Exception as exc:
        return {'available':False,'error':str(exc)}


class LocalModelClient:
    def __init__(self):
        self._completed_own_generation=False

    def inspect(self):
        try:
            tags=local_json('tags').get('models',[])
            installed=any(m.get('name')==MODEL and m.get('digest')==MODEL_DIGEST for m in tags)
            residency=local_json('ps')
            resources=resource_admission() if installed and residency.get('models')==[] else {'available':False,'not_checked':'Model unavailable or already resident'}
            available=installed and residency.get('models')==[] and resources['available']
            hold_stage=('ready' if available else 'model_unavailable' if not installed else
                        'model_busy' if residency.get('models') else 'residency_unknown' if residency.get('models')!=[] else
                        'capacity_unknown' if resources.get('error') else 'capacity_held')
            message={'ready':'Local layout model ready.','model_unavailable':'The exact local layout model is unavailable.',
                     'model_busy':'Another local model is resident.','residency_unknown':'Local model residency could not be verified.',
                     'capacity_unknown':'RAM/VRAM/GPU capacity could not be verified.',
                     'capacity_held':'Local RAM, VRAM or GPU activity has not met the required capacity gates.'}[hold_stage]
            return {'available':available, 'installed':installed,
                    'busy':bool(residency.get('models')), 'residency':residency,
                    'resources':resources,'hold_stage':hold_stage,'message':message}
        except Exception as exc:
            return {'available':False,'busy':False,'residency':None,'hold_stage':'residency_unknown',
                    'message':str(exc),'cleanup_known':False}

    def payload(self,messages):
        return {'model':MODEL,'messages':messages,'stream':False,'think':False,'keep_alive':0,'format':'json',
                'options':{'temperature':.15,'num_ctx':12288,'num_predict':5000}}

    @staticmethod
    def only_gpu_activity_held(admission):
        """A resample may never mask unknown readings, memory pressure or another model."""
        resources=admission.get('resources',{})
        try:
            return (admission.get('installed') is True and admission.get('residency',{}).get('models')==[]
                    and not admission.get('available') and not resources.get('error')
                    and resources['ram_available_bytes']>=15*1024**3
                    and resources['vram_available_mib']>=12*1024
                    and 25<=resources['gpu_utilization_percent']<=100)
        except (KeyError,TypeError,AttributeError):return False

    def generate(self,payload,*,allow_repair_resample=False,on_progress=None):
        admission=self.inspect()
        checks=[admission]
        resample_allowed=allow_repair_resample and self._completed_own_generation
        # This permission exists only in this client instance after its own exact,
        # complete response and observed empty residency. It is consumed once.
        self._completed_own_generation=False
        if resample_allowed:
            for index in range(GPU_RESAMPLES):
                if not self.only_gpu_activity_held(admission):break
                if on_progress:on_progress({'stage':'Waiting for GPU activity',
                    'message':'Previous local generation is released; checking GPU activity again in 2 seconds ('+str(index+1)+' of 3). No repair has been dispatched.'})
                time.sleep(GPU_RESAMPLE_SECONDS)
                admission=self.inspect();checks.append(admission)
        if not admission['available']:
            return {'dispatched':False,'admission':admission,'admission_checks':checks,'gpu_resamples':len(checks)-1,
                    'response':None,'cleanup_verified':None}
        response=None;error=None;residency=None
        if on_progress:on_progress({'stage':'Planning rooms locally','message':'Writing an original room program after capacity checks passed.'})
        try:
            response=local_json('chat',payload,timeout=180)
        except Exception as exc:
            error=type(exc).__name__+': '+str(exc)
        finally:
            try:residency=local_json('ps')
            except Exception as exc:
                error=(error+'; ' if error else '')+'Residency unknown: '+str(exc)
        cleanup=isinstance(residency,dict) and residency.get('models')==[]
        self._completed_own_generation=(cleanup and not error and isinstance(response,dict)
            and response.get('model')==MODEL and response.get('done') is True)
        return {'dispatched':True,'admission':admission,'admission_checks':checks,'gpu_resamples':len(checks)-1,
                'response':response,'error':error,'residency_after':residency,'cleanup_verified':cleanup}
