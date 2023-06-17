# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 09:42:49 2021

@author: Thomas
"""
import hashlib


def generate_transfer_key(run_dict):
    args = [(key, value) for key, value in run_dict.items()]
    args.sort()
    m = hashlib.md5()
    for key, value in args:
        m.update("({}, {})".format(key, value).encode('utf-8'))

    return m.hexdigest()


def split_dataframe(df, chunk_size=10000):
    chunks = list()
    num_chunks = len(df) // chunk_size + 1
    for i in range(num_chunks):
        chunks.append(df[i * chunk_size:(i + 1) * chunk_size])
    return chunks


def reverse_date(old_d):
    delim = "-"
    old_d = old_d.split(delim)[::-1]
    new_d = ""
    for x in old_d:
        new_d += (x + delim)
    new_d = new_d[:-1]

    return new_d
