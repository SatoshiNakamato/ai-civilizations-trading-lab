from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class LearningEvent:
    category:str; success:float; difficulty:float; novelty:float; description:str

@dataclass(slots=True)
class Intelligence:
    """Compact capability model with bounded learning history."""
    reasoning:float=100.; creativity:float=100.; research:float=100.; market_skill:float=100.; risk_awareness:float=100.; prediction_skill:float=100.; communication:float=100.; skepticism:float=100.; learning_rate:float=100.; experience:int=0; successful_research:int=0; failed_research:int=0; discoveries:int=0; validated_predictions:int=0; history:list[LearningEvent]=field(default_factory=list)
    history_limit:int=50
    @property
    def capability_score(self):
        return (self.reasoning+self.creativity+self.research+self.market_skill+self.risk_awareness+self.prediction_skill+self.communication+self.skepticism+self.learning_rate)/9
    def learn(self,category,success,difficulty,novelty,description):
        success=max(0.,min(1.,success)); difficulty=max(0.,min(1.,difficulty)); novelty=max(0.,min(1.,novelty)); self.experience+=1; self.history.append(LearningEvent(category,success,difficulty,novelty,str(description)[:160])); self.history=self.history[-self.history_limit:]; change=.05+.20*success+.10*difficulty+.10*novelty-.08*(1-success); self._apply(category,change); self.successful_research+=success>=.65; self.failed_research+=success<.65; self.discoveries+=success>=.8; self.validated_predictions+=category=='prediction' and success>=.7
    def _apply(self,category,change):
        attr={'reasoning':'reasoning','creativity':'creativity','research':'research','market':'market_skill','risk':'risk_awareness','prediction':'prediction_skill','communication':'communication','skepticism':'skepticism','learning':'learning_rate'}.get(category,'reasoning'); setattr(self,attr,max(1.,min(500.,getattr(self,attr)+change)))
    def learn_from_prediction(self,accuracy,difficulty=.5): self.learn('prediction',accuracy,difficulty,.5,'Validated prediction result')
    def learn_from_research(self,quality,difficulty=.5,novelty=.5): self.learn('research',quality,difficulty,novelty,'Research experiment completed')
    def learn_from_trade_result(self,performance,risk_quality): self.learn('market',performance,.7,.4,'Strategy result'); self.learn('risk',risk_quality,.7,.3,'Risk-management result')
    def learn_from_collaboration(self,usefulness): self.learn('communication',usefulness,.4,.3,'Collaboration')
    def profile(self):
        return {'capability_score':round(self.capability_score,3),'reasoning':round(self.reasoning,3),'creativity':round(self.creativity,3),'research':round(self.research,3),'market_skill':round(self.market_skill,3),'risk_awareness':round(self.risk_awareness,3),'prediction_skill':round(self.prediction_skill,3),'communication':round(self.communication,3),'skepticism':round(self.skepticism,3),'learning_rate':round(self.learning_rate,3),'experience':self.experience,'successful_research':self.successful_research,'failed_research':self.failed_research,'discoveries':self.discoveries,'validated_predictions':self.validated_predictions}
