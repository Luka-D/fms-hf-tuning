# Copyright The FMS HF Tuning Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Standard
from typing import Dict
import logging
import math

# Third Party
import transformers

# Local
from tuning.config import configs

logger = logging.getLogger(__name__)


def set_special_tokens_dict(
    tokenizer_name_or_path: str, tokenizer: transformers.PreTrainedTokenizer
) -> dict:
    """Creates a special tokens dictionary and sets the special tokens,
       depending on the tokenizer.

    Args:
        tokenizer_name_or_path: configs.ModelArguments.tokenizer_name_or_path
        tokenizer: transformers.PreTrainedTokenizer.

    Returns:
        dict: Special tokens for the tokenizer.
    """

    special_tokens_dict = {}
    if not tokenizer_name_or_path:
        # TODO: understand if we need to hardcode these here or just use defaults in model
        if isinstance(
            tokenizer, (transformers.LlamaTokenizer, transformers.LlamaTokenizerFast)
        ):
            special_tokens_dict["bos_token"] = "<s>"
            special_tokens_dict["eos_token"] = "</s>"
            special_tokens_dict["unk_token"] = "<unk>"
            special_tokens_dict["pad_token"] = "<pad>"
        elif isinstance(
            tokenizer, (transformers.GPT2Tokenizer, transformers.GPTNeoXTokenizerFast)
        ):
            special_tokens_dict["pad_token"] = "<pad>"

        # Add special tokens only when a custom tokenizer is not passed
        # TODO: we need to change this, perhaps follow what open instruct does?
        if tokenizer.pad_token is None:
            logger.warning("PAD token set to default, missing in tokenizer")
            special_tokens_dict["pad_token"] = configs.DEFAULT_PAD_TOKEN
        if tokenizer.eos_token is None:
            logger.warning("EOS token set to default, missing in tokenizer")
            special_tokens_dict["eos_token"] = configs.DEFAULT_EOS_TOKEN
        if tokenizer.bos_token is None:
            logger.warning("BOS token set to default, missing in tokenizer")
            special_tokens_dict["bos_token"] = configs.DEFAULT_BOS_TOKEN
        if tokenizer.unk_token is None:
            logger.warning("UNK token set to default, missing in tokenizer")
            special_tokens_dict["unk_token"] = configs.DEFAULT_UNK_TOKEN
        if (
            tokenizer.pad_token is not None
            and tokenizer.pad_token == tokenizer.eos_token
        ):
            logger.warning(
                "PAD token set to default, to make it different from eos token"
            )
            if tokenizer.eos_token != configs.DEFAULT_PAD_TOKEN:
                tokenizer.pad_token = configs.DEFAULT_PAD_TOKEN
                special_tokens_dict["pad_token"] = configs.DEFAULT_PAD_TOKEN
            else:
                tokenizer.eos_token = configs.DEFAULT_EOS_TOKEN
                special_tokens_dict["eos_token"] = configs.DEFAULT_EOS_TOKEN
    return special_tokens_dict


def tokenizer_and_embedding_resize(
    special_tokens_dict: Dict,
    tokenizer: transformers.PreTrainedTokenizer,
    model: transformers.PreTrainedModel,
    multiple_of: int = 1,
) -> dict:
    """Resize tokenizer and embedding.
    Args:
        special_tokens_dict: Dict containing special tokens to be added.
        tokenizer: transformers.PreTrainedTokenizer.
        model: transformers.PreTrainedModel.
        multiple_of: int , embeddings are resized to multiple of this.
    Return:
        dict: Metadata on number of added tokens.
    """
    num_new_tokens = tokenizer.add_special_tokens(special_tokens_dict)
    embedding_size = int(multiple_of * math.ceil(len(tokenizer) / multiple_of))
    num_new_tokens = num_new_tokens + embedding_size - len(tokenizer)
    model.resize_token_embeddings(embedding_size)
    if num_new_tokens > 0:
        input_embeddings = model.get_input_embeddings().weight.data
        output_embeddings = model.get_output_embeddings().weight.data

        input_embeddings_avg = input_embeddings[:-num_new_tokens].mean(
            dim=0, keepdim=True
        )
        output_embeddings_avg = output_embeddings[:-num_new_tokens].mean(
            dim=0, keepdim=True
        )

        input_embeddings[-num_new_tokens:] = input_embeddings_avg
        output_embeddings[-num_new_tokens:] = output_embeddings_avg
    return {"num_new_tokens": num_new_tokens, "new_embedding_size": embedding_size}
