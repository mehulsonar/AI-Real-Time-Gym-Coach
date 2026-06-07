from core.base_exercise import BaseExercise

class PushUpsDetector(BaseExercise):
    DOWN_THRESHOLD = 100
    UP_THRESHOLD = 160
    MIN_VISABILITY = 0.7

    LEFT_ELBOW = 26
    LEFT_HIP = 27
    RIGHT_ELBOW = 23
    RIGHT_HIP = 24

    def __init__(self):
        super().__init__()

    def reset(self):
        self.reps = 0
        self.stage = None

    def process(self, landmarks):
        left_elbow_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_ELBOW),
            self.get_point(landmarks, self.LEFT_HIP)
        )

        right_elbow_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_ELBOW),
            self.get_point(landmarks, self.RIGHT_HIP)
        )

        left_vis = landmarks[self.LEFT_ELBOW].visability
        right_vis = landmarks[self.RIGHT_ELBOW].visability

        if left_vis >= right_vis:
            elbow_angle = left_elbow_angle
            elbow_idx, hip_idx = self.LEFT_ELBOW, self.LEFT_HIP
        else:
            elbow_angle = right_elbow_angle
            elbow_idx, hip_idx = self.RIGHTT_ELBOW, self.RIGHT_HIP

        key_landmark_visible = landmarks[elbow_idx].visibility >= self.MIN_VISABILITY and landmarks[hip_idx].visibility

        if key_landmark_visible:
            if elbow_angle < self.DOWN_THRESHOLD:
                self.stage =  "down"
            
            if elbow_angle >= self.UP_THRESHOLD and self.stage == "down":
                self.stage = "up"
                self.reps += 1
            
            # if self.stage == "down":
        # Hip Position
        # body alignment
