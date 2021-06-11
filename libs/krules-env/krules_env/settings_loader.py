
import yaml
import os
from pathlib import Path


def load_from_path(base_path):

    def _expand_vars(d):
        for k, v in d.items():
            if type(v) is str:
                v = os.path.expandvars(v)
            elif type(v) is list:
                v = _expand_list_vars(v)
                # for i in range(len(v)):
                #     if type(v[i]) is str:
                #         os.path.expandvars(v[i])
                #     else:
                #         v[i] = _expand_vars(v[i])
            elif type(v) is dict:
                v = _expand_vars(v)
            d[k] = v

        return d

    def _expand_list_vars(l):
        for i in range(len(l)):
            if type(l[i]) is str:
                l[i] = os.path.expandvars(l[i])
            elif type(l[i]) is dict:
                l[i] = _expand_vars(l[i])
            elif type(l[i]) is list:
                l[i] = _expand_list_vars(l[i])
        return l

    settings = {}
    for root, dirs, files in os.walk(base_path):
        for f in files:
            if os.path.split(root)[-1].startswith(".."):
                continue
            else:
                pos = settings
                for p in Path(root).relative_to(base_path).parts:
                    if p not in pos:
                        pos[p] = {}
                    pos = pos[p]
                if os.path.splitext(f)[-1] in (".yaml", ".yml"):
                    pos.update(
                        _expand_vars(
                            yaml.load(open(os.path.join(root, f), "r"), Loader=yaml.FullLoader)
                        )
                    )
    return settings
