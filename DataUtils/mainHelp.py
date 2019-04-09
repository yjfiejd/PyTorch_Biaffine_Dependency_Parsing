# @Author : bamtercelboo
# @Datetime : 2018/9/20 16:00
# @File : mainHelp.py
# @Last Modify Time : 2018/9/20 16:00
# @Contact : bamtercelboo@{gmail.com, 163.com}

"""
    FILE :  mainHelp.py
    FUNCTION : None
"""


from DataUtils.Alphabet import *
from DataUtils.Batch_Iterator import *
from DataUtils.Embed import Embed
from Dataloader.DataLoader import DataLoader
from DataUtils.Common import seed_num, PAD
from Model.Biaffine_Parsing.Model import ParserModel
from Model.Biaffine_Parsing.Parser import BiaffineParser
from test import load_test_model
import shutil
import time
# random seed
torch.manual_seed(seed_num)
random.seed(seed_num)


# load data / create alphabet / create iterator
def preprocessing(config):
    """
    :param config: config
    :return:
    """
    print("Processing Data......")
    # read file
    data_loader = DataLoader(path=[config.train_file, config.dev_file, config.test_file], shuffle=True, config=config)
    train_data, dev_data, test_data = data_loader.dataLoader()
    print("train sentence {}, dev sentence {}, test sentence {}.".format(len(train_data), len(dev_data), len(test_data)))
    data_dict = {"train_data": train_data, "dev_data": dev_data, "test_data": test_data}
    if config.save_pkl is True:
        torch.save(obj=data_dict, f=os.path.join(config.pkl_directory, config.pkl_data))

    # create the alphabet
    alphabet = CreateAlphabet(min_freq=config.min_freq, train_data=train_data, config=config)
    alphabet_ext = CreateAlphabet(min_freq=1, train_data=train_data, dev_data=dev_data,
                                  test_data=test_data, config=config)
    alphabet.build_vocab()
    alphabet_ext.build_vocab()
    if config.save_pkl is True:
        alphabet_dict = {"alphabet": alphabet, "alphabet_ext": alphabet_ext}
        torch.save(obj=alphabet_dict, f=os.path.join(config.pkl_directory, config.pkl_alphabet))

    # reload data for alphabet is not None
    data_loader_alphabet = DataLoader(path=[config.train_file, config.dev_file, config.test_file], shuffle=True,
                                      config=config, alphabet=alphabet)
    train_data_alpha, dev_data_alpha, test_data_alpha = data_loader_alphabet.dataLoader()
    print("train sentence {}, dev sentence {}, test sentence {}.".format(len(train_data_alpha),
                                                                         len(dev_data_alpha), len(test_data_alpha)))
    data_dict = {"train_data_alpha": train_data_alpha, "dev_data_alpha": dev_data_alpha,
                 "test_data_alpha": test_data_alpha}
    if config.save_pkl is True:
        torch.save(obj=data_dict, f=os.path.join(config.pkl_directory, config.pkl_data))

    # create iterator
    create_iter = Iterators(batch_size=[config.batch_size, config.dev_batch_size, config.test_batch_size],
                            data=[train_data_alpha, dev_data_alpha, test_data_alpha], alphabet=alphabet, alphabet_ext=alphabet_ext,
                            config=config)
    train_iter, dev_iter, test_iter = create_iter.createIterator()
    iter_dict = {"train_iter": train_iter, "dev_iter": dev_iter, "test_iter": test_iter}
    if config.save_pkl is True:
        torch.save(obj=iter_dict, f=os.path.join(config.pkl_directory, config.pkl_iter))
    return train_iter, dev_iter, test_iter, alphabet, alphabet_ext


def save_dict2file(dict, path):
    """
    :param dict:  dict
    :param path:  path to save dict
    :return:
    """
    print("Saving dictionary")
    if os.path.exists(path):
        print("path {} is exist, deleted.".format(path))
    file = open(path, encoding="UTF-8", mode="w")
    for word, index in dict.items():
        # print(word, index)
        file.write(str(word) + "\t" + str(index) + "\n")
    file.close()
    print("Save dictionary finished.")


def save_dictionary(config):
    """
    :param config: config
    :return:
    """
    if config.save_dict is True:
        if os.path.exists(config.dict_directory): shutil.rmtree(config.dict_directory)
        if not os.path.isdir(config.dict_directory): os.makedirs(config.dict_directory)

        config.word_dict_path = "/".join([config.dict_directory, config.word_dict])
        config.ext_word_dict_path = "/".join([config.dict_directory, "_".join([config.word_dict, "ext.txt"])])
        print("word_dict_path : {}".format(config.word_dict_path))
        print("ext_word_dict_path : {}".format(config.ext_word_dict_path))
        save_dict2file(config.alphabet.word_alphabet.words2id, config.word_dict_path)
        save_dict2file(config.alphabet_ext.word_alphabet.words2id, config.ext_word_dict_path)
        # copy to mulu
        print("copy dictionary to {}".format(config.save_dir))
        shutil.copytree(config.dict_directory, "/".join([config.save_dir, config.dict_directory]))


def pre_embed(config, alphabet):
    """
    :param config: config
    :param alphabet:  alphabet dict
    :return:  pre-train embed
    """
    print("***************************************")
    pretrain_embed = None
    embed_types = ""
    if config.pretrained_embed and config.zeros:
        embed_types = "zero"
    elif config.pretrained_embed and config.avg:
        embed_types = "avg"
    elif config.pretrained_embed and config.uniform:
        embed_types = "uniform"
    elif config.pretrained_embed and config.nnembed:
        embed_types = "nn"
    if config.pretrained_embed is True:
        p = Embed(path=config.pretrained_embed_file, words_dict=alphabet.word_alphabet.id2words, embed_type=embed_types,
                  pad=PAD)
        pretrain_embed = p.get_embed()

        embed_dict = {"pretrain_embed": pretrain_embed}
        # pcl.save(obj=embed_dict, path=os.path.join(config.pkl_directory, config.pkl_embed))
        torch.save(obj=embed_dict, f=os.path.join(config.pkl_directory, config.pkl_embed))

    return pretrain_embed


def get_learning_algorithm(config):
    """
    :param config:  config
    :return:  optimizer algorithm
    """
    algorithm = None
    if config.adam is True:
        algorithm = "Adam"
    elif config.sgd is True:
        algorithm = "SGD"
    print("learning algorithm is {}.".format(algorithm))
    return algorithm


def get_params(config, alphabet, alphabet_ext):
    """
    :param config:
    :param alphabet:
    :param alphabet_ext:
    :return:
    """
    # get algorithm
    config.learning_algorithm = get_learning_algorithm(config)

    # save best model path
    config.save_best_model_path = config.save_best_model_dir
    if config.test is False:
        if os.path.exists(config.save_best_model_path):
            shutil.rmtree(config.save_best_model_path)

    # get params
    config.embed_num = alphabet.word_alphabet.vocab_size
    config.ext_embed_num = alphabet_ext.word_alphabet.vocab_size
    config.rel_size = alphabet.rel_alphabet.vocab_size
    config.word_PADID = alphabet.word_PADID
    config.ext_word_PADID = alphabet_ext.word_PADID
    config.word_ROOTID = alphabet.word_ROOTID
    config.alphabet = alphabet
    config.alphabet_ext = alphabet_ext
    print("embed_num : {}, ext_embed_num : {}, rel_size : {}".format(config.embed_num,
                                                                     config.ext_embed_num,
                                                                     config.rel_size))
    print("word_PADID {}, ext_word_PADID {}, word_ROOTID {}".format(config.word_PADID,
                                                                    config.ext_word_PADID,
                                                                    config.word_ROOTID))
    print_common()


def load_model(config):
    """
    :param config:  config
    :return:  nn model
    """
    print("***************************************")
    model = ParserModel(config)

    if config.device != cpu_device:
        model = model.to(config.device)
    if config.test is True:
        model = load_test_model(model, config)

    parser = BiaffineParser(model, config.word_ROOTID)

    print(model)
    print("Parser: ", parser)
    return parser


def load_data(config):
    """
    :param config:  config
    :return: batch data iterator and alphabet
    """
    print("load data for process or pkl data.")
    train_iter, dev_iter, test_iter = None, None, None
    alphabet, alphabet_ext = None, None
    start_time = time.time()
    if (config.train is True) and (config.process is True):
        print("process data")
        if os.path.exists(config.pkl_directory): shutil.rmtree(config.pkl_directory)
        if not os.path.isdir(config.pkl_directory): os.makedirs(config.pkl_directory)
        train_iter, dev_iter, test_iter, alphabet, alphabet_ext = preprocessing(config)
        config.pretrained_weight = pre_embed(config=config, alphabet=alphabet_ext)
    elif ((config.train is True) and (config.process is False)) or (config.test is True):
        print("load data from pkl file")
        # load alphabet from pkl
        # alphabet_dict = pcl.load(path=os.path.join(config.pkl_directory, config.pkl_alphabet))
        alphabet_dict = torch.load(f=os.path.join(config.pkl_directory, config.pkl_alphabet))
        print(alphabet_dict.keys())
        # alphabet = alphabet_dict["alphabet"]
        alphabet, alphabet_ext = alphabet_dict["alphabet"], alphabet_dict["alphabet_ext"]
        # load iter from pkl
        # iter_dict = pcl.load(path=os.path.join(config.pkl_directory, config.pkl_iter))
        iter_dict = torch.load(f=os.path.join(config.pkl_directory, config.pkl_iter))
        print(iter_dict.keys())
        train_iter, dev_iter, test_iter = iter_dict.values()
        # train_iter, dev_iter, test_iter = iter_dict["train_iter"], iter_dict["dev_iter"], iter_dict["test_iter"]
        # load embed from pkl
        if os.path.exists(os.path.join(config.pkl_directory, config.pkl_embed)):
            # embed_dict = pcl.load(os.path.join(config.pkl_directory, config.pkl_embed))
            embed_dict = torch.load(f=os.path.join(config.pkl_directory, config.pkl_embed))
            print(embed_dict.keys())
            embed = embed_dict["pretrain_embed"]
            config.pretrained_weight = embed
    end_time = time.time()
    print("Load Data Use Time {:.4f}".format(end_time - start_time))
    print("***************************************")

    return train_iter, dev_iter, test_iter, alphabet, alphabet_ext


