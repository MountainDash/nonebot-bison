import { Input, Tag, Tooltip } from "antd";
import { PresetColorType, PresetStatusColorType } from "antd/lib/_util/colors";
import { LiteralUnion } from "antd/lib/_util/type";
import React, { useRef, useState, useEffect } from "react";
import { PlusOutlined } from "@ant-design/icons";

interface InputTagProp {
  value?: Array<string>;
  onChange?: (value: Array<string>) => void;
  color?: LiteralUnion<PresetColorType | PresetStatusColorType, string>;
  addText?: string;
}
export function InputTag(prop: InputTagProp) {
  const [value, setValue] = useState<Array<string>>(prop.value || []);
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [editInputIndex, setEditInputIndex] = useState(-1);
  const [editInputValue, setEditInputValue] = useState("");
  const inputRef = useRef(null as any);
  const editInputRef = useRef(null as any);
  useEffect(() => {
    if (prop.value) {
      setValue(prop.value);
    }
  }, [prop.value]);
  useEffect(() => {
    if (inputVisible) {
      inputRef.current.focus();
    }
  }, [inputVisible]);
  useEffect(() => {
    if (editInputIndex !== -1) {
      editInputRef.current.focus();
    }
  }, [editInputIndex]);

  const handleClose = (removedTag: string) => {
    const tags = value.filter((tag) => tag !== removedTag);
    setValue((_) => tags);
    if (prop.onChange) {
      prop.onChange(tags);
    }
  };

  const showInput = () => {
    setInputVisible((_) => true);
  };

  const handleInputConfirm = () => {
    if (inputValue && value.indexOf(inputValue) === -1) {
      const newVal = [...value, inputValue];
      setValue((_) => newVal);
      if (prop.onChange) {
        prop.onChange(newVal);
      }
    }
    setInputVisible((_) => false);
    setInputValue((_) => "");
  };

  const handleEditInputChange = (e: any) => {
    setEditInputValue((_) => e.target.value);
  };

  const handleEditInputConfirm = () => {
    const newTags = value.slice();
    newTags[editInputIndex] = editInputValue;
    setValue((_) => newTags);
    if (prop.onChange) {
      prop.onChange(newTags);
    }
    setEditInputIndex((_) => -1);
    setEditInputValue((_) => "");
  };

  const handleInputChange = (e: any) => {
    setInputValue(e.target.value);
  };

  return (
    <>
      {value.map((tag, index) => {
        if (editInputIndex === index) {
          return (
            <Input
              ref={editInputRef}
              key={tag}
              size="small"
              value={editInputValue}
              onChange={handleEditInputChange}
              onBlur={handleEditInputConfirm}
              onPressEnter={handleInputConfirm}
            />
          );
        }
        const isLongTag = tag.length > 20;
        const tagElem = (
          <Tag
            color={prop.color || "default"}
            style={{ userSelect: "none" }}
            key={tag}
            closable
            onClose={() => handleClose(tag)}
          >
            <span
              onDoubleClick={(e) => {
                setEditInputIndex((_) => index);
                setEditInputValue((_) => tag);
                e.preventDefault();
              }}
            >
              {isLongTag ? `${tag.slice(0, 20)}...` : tag}
            </span>
          </Tag>
        );
        return isLongTag ? (
          <Tooltip title={tag} key={tag}>
            {tagElem}
          </Tooltip>
        ) : (
          tagElem
        );
      })}
      {inputVisible && (
        <Input
          ref={inputRef}
          type="text"
          size="small"
          style={{ width: "78px", marginRight: "8px", verticalAlign: "top" }}
          value={inputValue}
          onChange={handleInputChange}
          onBlur={handleInputConfirm}
          onPressEnter={handleInputConfirm}
        />
      )}
      {!inputVisible && (
        <Tag
          className="site-tag-plus"
          onClick={showInput}
          style={{
            background: "#fff",
            border: "dashed thin",
            borderColor: "#bfbfbf",
          }}
        >
          <PlusOutlined /> {prop.addText || "Add Tag"}
        </Tag>
      )}
    </>
  );
}
