/**
 * 本文件的作用是：实现 CreateSessionForm 对应的前端交互与界面展示。
 */
import { Button, DatePicker, Form, Input, InputNumber, Select } from "antd";
import dayjs from "dayjs";

interface CreateSessionFormValues {
  title: string;
  course_type: string;
  custom_course_type?: string;
  class_date: dayjs.Dayjs;
  duration_minutes: number;
  notes?: string;
}

interface CreateSessionFormProps {
  loading: boolean;
  onSubmit: (payload: {
    title: string;
    course_type: string;
    class_date: string;
    duration_minutes: number;
    notes?: string;
  }) => Promise<void>;
}

const courseOptions = [
  { label: "C 语言程序设计", value: "c_language" },
  { label: "C++ 程序设计", value: "cpp" },
  { label: "Python 程序设计", value: "python" },
  { label: "Java 程序设计", value: "java" },
  { label: "数据结构", value: "data_structures" },
  { label: "算法设计与分析", value: "algorithms" },
  { label: "数据库原理 / SQL", value: "database" },
  { label: "计算机网络", value: "computer_networks" },
  { label: "操作系统", value: "operating_systems" },
  { label: "计算机组成原理", value: "computer_organization" },
  { label: "Web 前端开发", value: "web_frontend" },
  { label: "Web 后端开发", value: "web_backend" },
  { label: "软件工程", value: "software_engineering" },
  { label: "人工智能基础", value: "ai_fundamentals" },
  { label: "机器学习", value: "machine_learning" },
  { label: "大数据技术", value: "big_data" },
  { label: "其他课程（自定义）", value: "__custom__" },
];

export function CreateSessionForm({ loading, onSubmit }: CreateSessionFormProps) {
  const [form] = Form.useForm<CreateSessionFormValues>();
  const courseType = Form.useWatch("course_type", form);

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{ course_type: "python", duration_minutes: 90, class_date: dayjs() }}
      onFinish={async (values) => {
        const finalCourseType = values.course_type === "__custom__"
          ? (values.custom_course_type || "其他课程").trim()
          : values.course_type;
        await onSubmit({
          title: values.title,
          course_type: finalCourseType,
          class_date: values.class_date.format("YYYY-MM-DD"),
          duration_minutes: values.duration_minutes,
          notes: values.notes,
        });
      }}
    >
      <div className="form-grid">
        <Form.Item label="课堂标题" name="title" rules={[{ required: true, message: "请输入课堂标题" }]}>
          <Input placeholder="例如：Python 条件语句与循环" />
        </Form.Item>
        <div>
          <Form.Item label="课程类型" name="course_type" rules={[{ required: true, message: "请选择课程类型" }]}>
            <Select showSearch optionFilterProp="label" options={courseOptions} />
          </Form.Item>
          {courseType === "__custom__" ? (
            <Form.Item
              name="custom_course_type"
              rules={[{ required: true, message: "请输入自定义课程类型" }]}
              style={{ marginTop: -8 }}
            >
              <Input placeholder="例如：嵌入式系统、数字电路、工程实践" maxLength={60} />
            </Form.Item>
          ) : null}
        </div>
        <Form.Item label="上课日期" name="class_date" rules={[{ required: true, message: "请选择日期" }]}>
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="课堂时长（分钟）" name="duration_minutes" rules={[{ required: true, message: "请输入时长" }]}>
          <InputNumber min={10} max={480} style={{ width: "100%" }} />
        </Form.Item>
      </div>
      <Form.Item label="备注" name="notes">
        <Input.TextArea rows={4} placeholder="记录这节课的教学目标、班级特点或其他备注" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={loading}>创建并进入工作台</Button>
    </Form>
  );
}
