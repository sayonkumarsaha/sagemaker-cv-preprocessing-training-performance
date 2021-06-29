import sagemaker
from sagemaker.pytorch import PyTorch
from sagemaker.inputs import FileSystemInput
from sagemaker.debugger import ProfilerConfig, FrameworkProfile, DetailedProfilingConfig
from datetime import datetime

def aug_exp_train(model_arch, batch_size, aug_operator, aug_load, instance_type):
    
    CURR_SM_ROLE = 'arn:aws:iam::154108359553:role/service-role/AmazonSageMaker-ExecutionRole-20210203T120788'

    BUCKET = 'dali-test'

    # Full size download of https://github.com/fastai/imagenette
    # 1.3GB — 13,395 images for 10 classes
    train_data_s3 = 's3://{}/{}'.format(BUCKET, 'imagenette2')

    model_ckpt_s3 = 's3://{}/{}'.format(BUCKET, 'training_jobs_checkpoints')
    src_code_s3 = 's3://{}/{}'.format(BUCKET, 'training_jobs')
    training_job_output_s3 = 's3://{}/{}'.format(BUCKET, 'training_jobs_output')

    profiler_config = ProfilerConfig(
            system_monitor_interval_millis = 100,
            framework_profile_params = FrameworkProfile(start_step = 1, num_steps = 100)
    )
    
    train_estimator = PyTorch(entry_point = 'sm_augmentation_train-script.py',
                              source_dir =  './src',
                              role = CURR_SM_ROLE,
                              framework_version = '1.8.1',
                              py_version = 'py3',

                              profiler_config = profiler_config,
                              debugger_hook_config = False,

                              instance_count = 1,
                              instance_type = instance_type,

                              output_path = training_job_output_s3,
                              code_location = src_code_s3,

                              hyperparameters = {'epochs': 3, 
                                                'backend': 'nccl',
                                                'pretrained-model-type': model_arch,
                                                'lr': 0.001,
                                                'batch-size': batch_size,
                                                'aug': aug_operator,
                                                'aug-load': aug_load
                            }
    )
    
    data_channels = {'train': sagemaker.inputs.TrainingInput(
                                            s3_data_type = 'S3Prefix',
                                            s3_data = train_data_s3,
                                            content_type='image/jpeg',
                                            input_mode='File'), 
                     
                     'val': sagemaker.inputs.TrainingInput(
                                            s3_data_type = 'S3Prefix',
                                            s3_data = train_data_s3,
                                            content_type='image/jpeg',
                                            input_mode='File') 
    }
    
    train_job_id = 'sm-aug-' + str(datetime.now().strftime("%H-%M-%S"))
    train_estimator.fit(inputs = data_channels, job_name = train_job_id)
    
    return train_job_id, train_estimator