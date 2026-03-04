

class WorkFlowInfo():
    def __init__(self,template_name):
        self.template_name = template_name
        self.prompt=None
        self.na_prompt=None
        self.seed = None
        self.scale = "1.0"
        self.image1 = None
        self.image2 = None
        self.image3 = None
        self.image4 = None
        self.ref_images_num = 0


# replace_map = {
#     "#prompt#": wf.prompt,
#     "#na_prompt#": wf.na_prompt,
#     "#seed#": wf.seed,
#     "#scale#": wf.scale,
#     "#image1#": wf.image1,
#     "#image2#": wf.image2,
#     "#image3#": wf.image3,
#     "#image4#": wf.image4,
# }
        
        
        


template_dict_replace={
    'qwen_edit_all.json':["#prompt#","#na_prompt#","#seed#","#scale#","#image1#"],
    'qwen_edit_all_batch.json':["#prompt#","#na_prompt#","#seed#","#scale#","#image1#","#image2#","#image3#","#image4#"],
    'z_image_turbo_16.json':["#prompt#","#na_prompt#","#seed#"],
}


