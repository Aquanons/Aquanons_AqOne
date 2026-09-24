import os

Import("env")

custom_src_dir = env.GetProjectOption("custom_src_dir")
env.Replace(PROJECT_SRC_DIR=os.path.join(env.subst("$PROJECT_DIR"), custom_src_dir))
