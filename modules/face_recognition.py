import os
import pickle
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from deepface import DeepFace
import config

class FaceRecognizer:
    def __init__(self):
        self.face_db_path = config.FACE_DB_PATH
        self.cache_dir = config.CACHE_DIR
        self.model_name = config.DEEPFACE_MODEL
        self.detector_backend = config.DEEPFACE_DETECTOR
        self.distance_metric = config.DEEPFACE_DISTANCE_METRIC

        # 确保目录存在
        os.makedirs(self.face_db_path, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def load_face_database(self, class_names):
        """
        加载人脸库
        Args:
            class_names: 班级名称列表，如['教育技术', '大数据']
        Returns:
            {student_name: {'embedding': embedding_vector, 'student_id': id}, ...}
        """
        # 生成缓存文件名
        cache_filename = '_'.join(sorted(class_names)) + '.pkl'
        cache_path = os.path.join(self.cache_dir, cache_filename)

        # 如果缓存存在，直接加载
        if os.path.exists(cache_path):
            print(f"加载缓存: {cache_filename}")
            with open(cache_path, 'rb') as f:
                return pickle.load(f)

        # 否则构建人脸库
        print(f"构建人脸库: {class_names}")
        face_db = {}

        from modules.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        for class_name in class_names:
            class_dir = os.path.join(self.face_db_path, class_name)
            if not os.path.exists(class_dir):
                continue

            # 获取该班级的所有学生
            cursor.execute('''
                SELECT s.id, s.name, s.image_path
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE c.name = ?
            ''', (class_name,))

            students = cursor.fetchall()

            for student in students:
                student_id = student['id']
                student_name = student['name']
                image_path = student['image_path']

                if os.path.exists(image_path):
                    try:
                        # 提取人脸特征
                        embedding = DeepFace.represent(
                            img_path=image_path,
                            model_name=self.model_name,
                            detector_backend=self.detector_backend,
                            enforce_detection=False
                        )[0]['embedding']

                        face_db[student_name] = {
                            'embedding': embedding,
                            'student_id': student_id
                        }
                        print(f"  - 已提取: {student_name}")
                    except Exception as e:
                        print(f"  - 提取失败 {student_name}: {e}")

        conn.close()

        # 保存缓存
        with open(cache_path, 'wb') as f:
            pickle.dump(face_db, f)

        print(f"人脸库构建完成，共 {len(face_db)} 人")
        return face_db

    def recognize_faces(self, image_base64, class_names, threshold=None):
        """
        识别图片中的所有人脸
        Args:
            image_base64: base64编码的图片
            class_names: 班级名称列表
            threshold: 相似度阈值
        Returns:
            识别结果列表
        """
        if threshold is None:
            threshold = config.SIMILARITY_THRESHOLD

        # 加载人脸库
        face_db = self.load_face_database(class_names)

        if not face_db:
            return []

        # 解码base64图片
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))

        # 保存临时图片
        temp_path = os.path.join(self.cache_dir, 'temp_capture.jpg')
        image.save(temp_path)

        results = []

        try:
            # 提取所有人脸特征（支持多人脸）
            embeddings_list = DeepFace.represent(
                img_path=temp_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            # 对每个检测到的人脸进行识别
            for embedding_obj in embeddings_list:
                face_embedding = embedding_obj['embedding']

                # 与人脸库中所有人比较
                best_match = None
                best_similarity = -1

                for student_name, data in face_db.items():
                    db_embedding = data['embedding']

                    # 计算余弦相似度
                    similarity = self._cosine_similarity(face_embedding, db_embedding)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = {
                            'name': student_name,
                            'student_id': data['student_id'],
                            'confidence': round(best_similarity * 100, 2)
                        }

                # 判断是否识别成功（相似度阈值为1-threshold，因为距离越小越相似）
                if best_match and best_similarity >= (1 - threshold):
                    results.append(best_match)

        except Exception as e:
            print(f"人脸识别错误: {e}")

        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return results

    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def invalidate_cache(self, class_name):
        """删除包含指定班级名称的所有缓存文件"""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl') and class_name in filename:
                cache_path = os.path.join(self.cache_dir, filename)
                os.remove(cache_path)
                print(f"已删除缓存: {filename}")
